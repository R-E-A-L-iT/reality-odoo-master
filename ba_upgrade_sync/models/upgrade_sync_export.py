# -*- coding: utf-8 -*-
"""Export every business action done by users between two dates.

The list merges two sources, sorted by date:

* **history**: rebuilt from what Odoo 17 already stores, so it works for dates
  before this module was installed:
    - creation of a record (``create_date`` / ``create_uid``);
    - every tracked field change in the chatter (``mail.tracking.value``), which
      gives the user and the date of e.g. quotation sent, order confirmed,
      invoice posted, opportunity stage / won / lost, salesperson changes...;
    - e-mails sent to the customer from a quotation / invoice.
* **capture**: the ``upgrade.sync.event`` rows recorded by this module once
  capture is enabled (more detailed: every edit, with a full JSON snapshot).

With the "Both" source, history is used before the first captured event and
captured events after it, so the same action is not listed twice.
"""
import base64
import csv
import io
import json
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# model -> action prefix used in the export
PREFIX = {
    "res.partner": "partner",
    "product.template": "product",
    "crm.lead": "lead",
    "sale.order": "sale",
    "account.move": "invoice",
}
INVOICE_TYPES = ("out_invoice", "out_refund")
BATCH = 1000


class UpgradeSyncExportWizard(models.TransientModel):
    _name = "upgrade.sync.export.wizard"
    _description = "Export User Actions (Odoo 17)"

    date_from = fields.Datetime("Start date", required=True,
                                default=lambda self: fields.Datetime.now().replace(hour=0, minute=0, second=0))
    date_to = fields.Datetime("End date", required=True, default=fields.Datetime.now)
    source = fields.Selection([
        ("both", "History + captured events"),
        ("history", "History only (chatter / creation)"),
        ("capture", "Captured events only"),
    ], default="both", required=True)
    include_partners = fields.Boolean("Contacts", default=True)
    include_products = fields.Boolean("Products", default=True)
    include_crm = fields.Boolean("CRM", default=True)
    include_sales = fields.Boolean("Sales", default=True)
    include_invoices = fields.Boolean("Invoices / credit notes", default=True)
    include_field_changes = fields.Boolean(
        "Other tracked field changes", default=True,
        help="Also list tracked changes that are not a status change "
             "(salesperson, customer, expected revenue, ...).")
    include_payload = fields.Boolean(
        "Include record snapshot",
        help="Add the JSON snapshot of the record. Captured events carry the snapshot taken "
             "at the time of the action; history lines get the record's current state.")
    output_format = fields.Selection([("json", "JSON"), ("csv", "CSV")], default="json", required=True)

    file_data = fields.Binary("File", readonly=True, attachment=False)
    file_name = fields.Char(readonly=True)
    line_count = fields.Integer("Actions", readonly=True)
    summary = fields.Text(readonly=True)

    # ------------------------------------------------------------------
    def _models(self):
        selected = []
        if self.include_partners:
            selected.append("res.partner")
        if self.include_products:
            selected.append("product.template")
        if self.include_crm:
            selected.append("crm.lead")
        if self.include_sales:
            selected.append("sale.order")
        if self.include_invoices:
            selected.append("account.move")
        return selected

    def action_generate(self):
        self.ensure_one()
        if self.date_from > self.date_to:
            raise UserError(_("The start date must be before the end date."))
        model_names = self._models()
        if not model_names:
            raise UserError(_("Select at least one type of document."))

        # per-run cache of selection label -> value maps (see _selection_label_map)
        self = self.with_context(_upgrade_sync_label_cache={})
        lines = []
        capture_start = self._capture_start()
        if self.source in ("history", "both"):
            history_to = self.date_to
            if self.source == "both" and capture_start:
                history_to = min(self.date_to, capture_start)
            if self.date_from < history_to or self.source == "history":
                lines += self._history_lines(model_names, self.date_from, history_to,
                                             strict_end=self.source == "both" and bool(capture_start))
        if self.source in ("capture", "both"):
            lines += self._captured_lines(model_names)

        lines.sort(key=lambda l: (l["date"], l["_order"], l["model"], l["record_id"]))
        for index, line in enumerate(lines, 1):
            line.pop("_order", None)
            line["sequence"] = index

        stamp = "%s_%s" % (self.date_from.strftime("%Y%m%d"), self.date_to.strftime("%Y%m%d"))
        if self.output_format == "json":
            content = json.dumps({
                "database": self.env.cr.dbname,
                "odoo_version": "17.0",
                "generated_at": fields.Datetime.to_string(fields.Datetime.now()),
                "generated_by": self.env.user.login,
                "date_from": fields.Datetime.to_string(self.date_from),
                "date_to": fields.Datetime.to_string(self.date_to),
                "source": self.source,
                "capture_started_at": capture_start and fields.Datetime.to_string(capture_start),
                "count": len(lines),
                "actions": lines,
            }, indent=2, default=str, ensure_ascii=False).encode()
            name = "user_actions_%s.json" % stamp
        else:
            content = self._to_csv(lines)
            name = "user_actions_%s.csv" % stamp

        counts = defaultdict(int)
        for line in lines:
            counts[line["action"]] += 1
        self.write({
            "file_data": base64.b64encode(content),
            "file_name": name,
            "line_count": len(lines),
            "summary": "\n".join("%s: %s" % (k, counts[k]) for k in sorted(counts)) or _("No action found."),
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    # ------------------------------------------------------------------
    # Captured events
    # ------------------------------------------------------------------
    def _capture_start(self):
        first = self.env["upgrade.sync.event"].sudo().search([], order="create_date asc, id asc", limit=1)
        return first.create_date if first else False

    def _captured_lines(self, model_names):
        events = self.env["upgrade.sync.event"].sudo().search([
            ("create_date", ">=", self.date_from),
            ("create_date", "<=", self.date_to),
            ("model", "in", model_names),
        ], order="id asc")
        lines = []
        for event in events:
            payload = {}
            try:
                payload = json.loads(event.payload or "{}")
            except ValueError:
                pass
            snap = payload.get("record") or {}
            line = self._line(
                date=event.create_date, action=event.event_type, model=event.model,
                record_id=event.res_id, record_name=event.res_name,
                user=event.user_id, source="capture", order=2,
                related=self._related_from_snapshot(event.model, snap),
            )
            line.update({
                "event_uuid": event.name,
                "event_id": event.id,
                "root_model": event.root_model,
                "root_id": event.root_id,
            })
            if payload.get("extra"):
                line["params"] = payload["extra"]
            if self.include_payload:
                line["snapshot"] = snap
            lines.append(line)
        return lines

    @api.model
    def _related_from_snapshot(self, model, snap):
        keys = {
            "sale.order": ("partner_id", "opportunity_id", "user_id", "company_id"),
            "account.move": ("partner_id", "reversed_entry_id", "company_id"),
            "crm.lead": ("partner_id", "user_id", "team_id", "stage_id", "company_id"),
            "res.partner": ("parent_id", "company_id"),
            "product.template": ("categ_id", "company_id"),
        }.get(model, ())
        related = {k: (snap.get(k) or {}).get("id") for k in keys if snap.get(k)}
        if model == "account.move" and snap.get("sale_order_ids"):
            related["sale_order_ids"] = [r["id"] for r in snap["sale_order_ids"]]
        return related

    # ------------------------------------------------------------------
    # History (works for dates before capture was enabled)
    # ------------------------------------------------------------------
    def _history_lines(self, model_names, date_from, date_to, strict_end=False):
        end_op = "<" if strict_end else "<="
        lines = []
        for model in model_names:
            lines += self._creation_lines(model, date_from, date_to, end_op)
        lines += self._tracking_lines(model_names, date_from, date_to, end_op)
        lines += self._email_lines(model_names, date_from, date_to, end_op)
        return lines

    def _base_domain(self, model):
        if model == "account.move":
            return [("move_type", "in", INVOICE_TYPES)]
        if model == "res.partner":
            # partners of internal users are not business contacts
            return [("user_ids", "=", False)]
        return []

    def _creation_lines(self, model, date_from, date_to, end_op):
        Model = self.env[model].sudo().with_context(active_test=False)
        records = Model.search(self._base_domain(model) + [
            ("create_date", ">=", date_from), ("create_date", end_op, date_to),
        ], order="create_date asc, id asc")
        lines = []
        for record in records:
            action = "%s.create" % PREFIX[model]
            params = {}
            if model == "account.move":
                orders = record.invoice_line_ids.sale_line_ids.order_id
                if record.reversed_entry_id:
                    action = "invoice.reverse"
                    params["reversed_entry_id"] = record.reversed_entry_id.id
                elif orders:
                    action = "invoice.create_from_sale"
                    params["sale_order_ids"] = orders.ids
            line = self._line(
                date=record.create_date, action=action, model=model, record_id=record.id,
                record_name=record.display_name, user=record.create_uid, source="history", order=0,
                related=self._related_from_record(record),
            )
            if params:
                line["params"] = params
            if self.include_payload:
                line["snapshot"] = self.env["upgrade.sync.serializer"]._snapshot(record)
            lines.append(line)
        return lines

    def _tracking_lines(self, model_names, date_from, date_to, end_op):
        Message = self.env["mail.message"].sudo()
        lines = []
        for model in model_names:
            messages = Message.search([
                ("model", "=", model),
                ("tracking_value_ids", "!=", False),
                ("date", ">=", date_from), ("date", end_op, date_to),
            ], order="date asc, id asc")
            records = self._existing(model, set(messages.mapped("res_id")))
            for message in messages:
                record = records.get(message.res_id)
                if record is None:
                    continue
                user = message.create_uid or message.author_id.user_ids[:1]
                actions, changes = self._actions_from_tracking(model, record, message.tracking_value_ids)
                for action, params in actions:
                    lines.append(self._history_change_line(message, record, user, action, changes, params))
                if not actions and changes and self.include_field_changes:
                    lines.append(self._history_change_line(
                        message, record, user, "%s.update" % PREFIX[model], changes, {}))
        return lines

    def _history_change_line(self, message, record, user, action, changes, params):
        line = self._line(
            date=message.date, action=action, model=record._name, record_id=record.id,
            record_name=record.display_name, user=user, source="history", order=1,
            related=self._related_from_record(record),
        )
        line["changes"] = changes
        line["message_id"] = message.id
        if params:
            line["params"] = params
        if self.include_payload:
            line["snapshot"] = self.env["upgrade.sync.serializer"]._snapshot(record)
        return line

    def _existing(self, model, ids):
        Model = self.env[model].sudo().with_context(active_test=False)
        domain = [("id", "in", list(ids))] + self._base_domain(model)
        return {r.id: r for r in Model.search(domain)} if ids else {}

    def _actions_from_tracking(self, model, record, trackings):
        """Turn a chatter tracking message into business actions."""
        changes = []
        actions = []
        for tracking in trackings:
            fname = tracking.field_id.name or (tracking.field_info or {}).get("name")
            old, new = self._tracking_values(record, fname, tracking)
            changes.append({
                "field": fname,
                "field_label": tracking.field_id.field_description or fname,
                "old": old,
                "new": new,
                "old_display": tracking.old_value_char or old,
                "new_display": tracking.new_value_char or new,
            })
            action = self._status_action(model, fname, old, new)
            if action:
                actions.append((action, {"from": old, "to": new}))
        return actions, changes

    def _tracking_values(self, record, fname, tracking):
        field = record._fields.get(fname)
        ftype = field.type if field else None
        if ftype == "many2one":
            return tracking.old_value_integer or False, tracking.new_value_integer or False
        if ftype in ("integer", "boolean"):
            if ftype == "boolean":
                # booleans are tracked as integers 0/1
                return bool(tracking.old_value_integer), bool(tracking.new_value_integer)
            return tracking.old_value_integer, tracking.new_value_integer
        if ftype in ("float", "monetary"):
            return tracking.old_value_float, tracking.new_value_float
        if ftype in ("date", "datetime"):
            return (tracking.old_value_datetime and fields.Datetime.to_string(tracking.old_value_datetime),
                    tracking.new_value_datetime and fields.Datetime.to_string(tracking.new_value_datetime))
        if ftype == "selection":
            # chatter stores the *label* (in the writer's language): map back to the key
            labels = self._selection_label_map(record, fname)
            return (labels.get(tracking.old_value_char, tracking.old_value_char or False),
                    labels.get(tracking.new_value_char, tracking.new_value_char or False))
        return tracking.old_value_char or tracking.old_value_text or False, \
            tracking.new_value_char or tracking.new_value_text or False

    @api.model
    def _selection_label_map(self, record, fname):
        cache = self.env.context.get("_upgrade_sync_label_cache")
        key = (record._name, fname)
        if cache is not None and key in cache:
            return cache[key]
        mapping = {}
        langs = [code for code, _name in self.env["res.lang"].get_installed()]
        for lang in set(langs) | {"en_US"}:
            description = record.with_context(lang=lang).fields_get([fname], ["selection"]).get(fname, {})
            for value, label in description.get("selection") or []:
                mapping[label] = value
                mapping[value] = value
        if cache is not None:
            cache[key] = mapping
        return mapping

    def _status_action(self, model, fname, old, new):
        if model == "sale.order" and fname == "state":
            if new == "sent" and old == "draft":
                return "sale.sent"
            if new == "sale":
                return "sale.confirm"
            if new == "cancel":
                return "sale.cancel"
            if new == "draft" and old == "cancel":
                return "sale.draft"
        if model == "account.move" and fname == "state":
            if new == "posted":
                return "invoice.post"
            if new == "cancel":
                return "invoice.cancel"
            if new == "draft":
                return "invoice.draft"
        if model == "account.move" and fname == "payment_state":
            return "invoice.payment_state"
        if model == "crm.lead" and fname == "stage_id":
            stage = self.env["crm.stage"].sudo().browse(new).exists() if new else None
            return "lead.won" if stage and stage.is_won else "lead.stage"
        if model == "crm.lead" and fname == "active":
            return "lead.lost" if old and not new else "lead.restore"
        if model == "crm.lead" and fname == "user_id":
            return "lead.assign"
        if model in ("sale.order", "account.move") and fname in ("user_id", "invoice_user_id"):
            return "%s.assign" % PREFIX[model]
        return None

    def _email_lines(self, model_names, date_from, date_to, end_op):
        """E-mails sent to the customer from quotations / invoices."""
        lines = []
        comment = self.env.ref("mail.mt_comment", raise_if_not_found=False)
        for model in set(model_names) & {"sale.order", "account.move"}:
            messages = self.env["mail.message"].sudo().search([
                ("model", "=", model),
                ("message_type", "in", ("comment", "email")),
                ("subtype_id", "=", comment.id if comment else False),
                ("partner_ids", "!=", False),
                ("date", ">=", date_from), ("date", end_op, date_to),
            ], order="date asc, id asc")
            records = self._existing(model, set(messages.mapped("res_id")))
            for message in messages:
                record = records.get(message.res_id)
                if record is None:
                    continue
                user = message.create_uid or message.author_id.user_ids[:1]
                line = self._line(
                    date=message.date, action="%s.email_sent" % PREFIX[model], model=model,
                    record_id=record.id, record_name=record.display_name, user=user,
                    source="history", order=1, related=self._related_from_record(record),
                )
                line["message_id"] = message.id
                line["params"] = {
                    "subject": message.subject or record.display_name,
                    "recipient_partner_ids": message.partner_ids.ids,
                    "attachment_count": len(message.attachment_ids),
                }
                lines.append(line)
        return lines

    @api.model
    def _related_from_record(self, record):
        model = record._name
        if model == "sale.order":
            return {k: v for k, v in {
                "partner_id": record.partner_id.id,
                "opportunity_id": record.opportunity_id.id,
                "user_id": record.user_id.id,
                "company_id": record.company_id.id,
                "invoice_ids": record.invoice_ids.ids,
            }.items() if v}
        if model == "account.move":
            return {k: v for k, v in {
                "partner_id": record.partner_id.id,
                "sale_order_ids": record.invoice_line_ids.sale_line_ids.order_id.ids,
                "reversed_entry_id": record.reversed_entry_id.id,
                "company_id": record.company_id.id,
            }.items() if v}
        if model == "crm.lead":
            return {k: v for k, v in {
                "partner_id": record.partner_id.id,
                "user_id": record.user_id.id,
                "team_id": record.team_id.id,
                "stage_id": record.stage_id.id,
                "order_ids": record.order_ids.ids,
                "company_id": record.company_id.id,
            }.items() if v}
        if model == "res.partner":
            return {k: v for k, v in {"parent_id": record.parent_id.id,
                                      "company_id": record.company_id.id}.items() if v}
        return {}

    # ------------------------------------------------------------------
    @api.model
    def _line(self, date, action, model, record_id, record_name, user, source, order, related):
        user = user[:1] if user else user
        return {
            "sequence": 0,
            "date": fields.Datetime.to_string(date),
            "action": action,
            "model": model,
            "record_id": record_id,
            "record_name": record_name,
            "user_id": user.id if user else False,
            "user_login": user.login if user else False,
            "user_name": user.name if user else False,
            "related": related,
            "source": source,
            "_order": order,
        }

    @api.model
    def _to_csv(self, lines):
        columns = ["sequence", "date", "action", "model", "record_id", "record_name", "user_id",
                   "user_login", "user_name", "source", "related", "changes", "params", "event_uuid",
                   "message_id"]
        if self.include_payload:
            columns.append("snapshot")
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        for line in lines:
            row = dict(line)
            for key in ("related", "changes", "params", "snapshot"):
                if key in row:
                    row[key] = json.dumps(row[key], default=str, ensure_ascii=False)
            writer.writerow(row)
        return buffer.getvalue().encode("utf-8-sig")
