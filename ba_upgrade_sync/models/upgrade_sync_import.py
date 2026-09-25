# -*- coding: utf-8 -*-
"""Import the "Export User Actions" file produced by Odoo 17.

Each line of the file (one user action) becomes an ``upgrade.sync.event``;
the normal replay engine then recreates the actions in Odoo 19 (same ordering,
dependency handling, retries, mapping and comparison as the live sync).

* Lines captured live in Odoo 17 keep their event UUID, so an action that was
  both fetched and imported is replayed once.
* History lines get a deterministic UUID (database + action + record + date),
  so importing the same file twice does not duplicate anything.
* History lines are ordered by their date and always before live-captured
  events (they describe the period before capture was enabled).
"""
import base64
import csv
import io
import json
import uuid
from datetime import datetime, timezone

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# action written by the Odoo 17 export -> replay event type in Odoo 19
# (None = informational only, not replayed)
ACTION_TO_EVENT = {
    "partner.create": "partner.upsert",
    "partner.update": "partner.upsert",
    "partner.upsert": "partner.upsert",
    "product.create": "product.upsert",
    "product.update": "product.upsert",
    "product.upsert": "product.upsert",
    "lead.create": "lead.upsert",
    "lead.update": "lead.upsert",
    "lead.upsert": "lead.upsert",
    "lead.assign": "lead.upsert",
    "lead.restore": "lead.upsert",
    "lead.stage": "lead.stage",
    "lead.won": "lead.won",
    "lead.lost": "lead.lost",
    "sale.create": "sale.upsert",
    "sale.update": "sale.upsert",
    "sale.upsert": "sale.upsert",
    "sale.assign": "sale.upsert",
    "sale.sent": "sale.sent",
    "sale.email_sent": "sale.sent",
    "sale.confirm": "sale.confirm",
    "sale.cancel": "sale.cancel",
    "sale.draft": "sale.draft",
    "invoice.create": "invoice.upsert",
    "invoice.update": "invoice.upsert",
    "invoice.upsert": "invoice.upsert",
    "invoice.assign": "invoice.upsert",
    "invoice.create_from_sale": "invoice.create_from_sale",
    "invoice.post": "invoice.post",
    "invoice.cancel": "invoice.cancel",
    "invoice.draft": "invoice.draft",
    "invoice.reverse": "invoice.reverse",
    "invoice.email_sent": None,
    "invoice.payment_state": None,
}
UUID_NAMESPACE = uuid.UUID("6f1d3c5e-9b7a-4e21-8d3f-2a5c7e9b1d40")
# History lines use the action time (seconds since 1970) shifted below zero, so
# they sort by date and before live-captured events (whose sequence is the
# positive Odoo 17 event id).
HISTORY_SEQUENCE_OFFSET = 2_100_000_000


class UpgradeSyncImportWizard(models.TransientModel):
    _name = "upgrade.sync.import.wizard"
    _description = "Import User Actions File (from Odoo 17)"

    file_data = fields.Binary("Actions file", required=True, attachment=False)
    file_name = fields.Char()
    process_now = fields.Boolean(
        "Replay immediately", default=True,
        help="Replay the imported actions right away (respects the Dry run setting). "
             "Otherwise they wait for 'Process Now' or the scheduled action.")
    dry_run = fields.Boolean(related="config_id.dry_run", readonly=False)
    config_id = fields.Many2one(
        "upgrade.sync.config", default=lambda self: self.env["upgrade.sync.config"]._get_config())

    state = fields.Selection([("draft", "Draft"), ("done", "Done")], default="draft")
    import_batch = fields.Char(readonly=True)
    summary = fields.Text(readonly=True)
    imported_count = fields.Integer("Imported", readonly=True)
    duplicate_count = fields.Integer("Already imported", readonly=True)
    skipped_count = fields.Integer("Not replayable", readonly=True)
    success_count = fields.Integer("Replayed OK", readonly=True)
    failed_count = fields.Integer("Failed / waiting", readonly=True)

    # ------------------------------------------------------------------
    def action_import(self):
        self.ensure_one()
        header, lines = self._read_file()
        batch = "%s @ %s" % (self.file_name or "file", fields.Datetime.to_string(fields.Datetime.now()))
        Event = self.env["upgrade.sync.event"].sudo()
        database = header.get("database") or "odoo17"

        prepared, skipped = [], []
        for line in lines:
            vals, reason = self._prepare_event(line, database, batch)
            if vals:
                prepared.append(vals)
            else:
                skipped.append("#%s %s %s %s: %s" % (
                    line.get("sequence"), line.get("action"), line.get("model"), line.get("record_id"), reason))

        missing_snapshot = [s for s in skipped if "snapshot" in s]
        if missing_snapshot and not prepared:
            raise UserError(_(
                "The file has no record snapshots. In Odoo 17, run Export User Actions again with "
                "'Include record snapshot' ticked, then import the new file."))

        known = set(Event.search([("event_uuid", "in", [v["event_uuid"] for v in prepared])]).mapped("event_uuid"))
        new_vals, seen = [], set(known)
        for vals in prepared:
            if vals["event_uuid"] in seen:
                continue
            seen.add(vals["event_uuid"])
            new_vals.append(vals)
        events = Event.create(new_vals) if new_vals else Event

        if self.process_now and events:
            events._process()

        states = events.mapped("state")
        summary = [
            _("File: %s", self.file_name or ""),
            _("Period: %(start)s -> %(end)s (Odoo 17 database %(db)s)",
              start=header.get("date_from") or "?", end=header.get("date_to") or "?", db=database),
            _("Lines in file: %s", len(lines)),
            _("Imported: %s", len(events)),
            _("Already imported before (skipped): %s", len(prepared) - len(new_vals)),
            _("Not replayable (skipped): %s", len(skipped)),
        ]
        if skipped:
            summary += [""] + skipped[:50] + ([_("... and %s more", len(skipped) - 50)] if len(skipped) > 50 else [])
        self.write({
            "state": "done",
            "import_batch": batch,
            "summary": "\n".join(summary),
            "imported_count": len(events),
            "duplicate_count": len(prepared) - len(new_vals),
            "skipped_count": len(skipped),
            "success_count": sum(1 for s in states if s in ("success", "dry_run_ok")),
            "failed_count": sum(1 for s in states if s in ("failed", "waiting", "pending")),
        })
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_open_events(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported actions"),
            "res_model": "upgrade.sync.event",
            "view_mode": "list,form",
            "domain": [("import_batch", "=", self.import_batch)],
            "context": {"search_default_group_state": 1},
        }

    # ------------------------------------------------------------------
    # File reading
    # ------------------------------------------------------------------
    def _read_file(self):
        raw = base64.b64decode(self.file_data or b"")
        if not raw:
            raise UserError(_("The file is empty."))
        name = (self.file_name or "").lower()
        text = raw.decode("utf-8-sig", errors="replace")
        if name.endswith(".csv") or not text.lstrip().startswith(("{", "[")):
            return {}, self._read_csv(text)
        try:
            data = json.loads(text)
        except ValueError as exc:
            raise UserError(_("This is not a valid JSON file: %s", exc)) from None
        if isinstance(data, list):
            return {}, data
        if not isinstance(data, dict) or not isinstance(data.get("actions"), list):
            raise UserError(_("Unexpected file format: an 'actions' list is required. "
                              "Use the file produced by 'Export User Actions' in Odoo 17."))
        return data, data["actions"]

    @api.model
    def _read_csv(self, text):
        lines = []
        for row in csv.DictReader(io.StringIO(text)):
            line = dict(row)
            for key in ("related", "changes", "params", "snapshot"):
                if line.get(key):
                    try:
                        line[key] = json.loads(line[key])
                    except ValueError:
                        line[key] = {}
            for key in ("sequence", "record_id", "user_id", "message_id"):
                if line.get(key) not in (None, ""):
                    try:
                        line[key] = int(line[key])
                    except ValueError:
                        pass
            lines.append(line)
        return lines

    # ------------------------------------------------------------------
    # Line -> event
    # ------------------------------------------------------------------
    @api.model
    def _event_type_for(self, action):
        """Extension point: map an exported action to a replay event type."""
        return ACTION_TO_EVENT.get(action, action if self.env["upgrade.sync.handler"]
                                   ._get_handler_method(action or "") else None)

    @api.model
    def _prepare_event(self, line, database, batch):
        action = line.get("action")
        model = line.get("model")
        record_id = line.get("record_id")
        if not (action and model and record_id):
            return None, _("incomplete line")
        event_type = self._event_type_for(action)
        if not event_type:
            return None, _("informational action, nothing to replay")
        snapshot = line.get("snapshot") or {}
        if not snapshot:
            return None, _("no record snapshot (export with 'Include record snapshot')")
        snapshot.setdefault("id", record_id)
        snapshot.setdefault("model", model)

        extra = dict(line.get("params") or {})
        if event_type == "invoice.create_from_sale":
            extra.setdefault("grouped", False)
            extra.setdefault("final", False)
        if event_type == "invoice.reverse" and not snapshot.get("reversed_entry_id") and extra.get("reversed_entry_id"):
            snapshot["reversed_entry_id"] = {"model": "account.move", "id": extra["reversed_entry_id"],
                                             "name": "", "create_date": None, "keys": {}}

        is_capture = line.get("source") == "capture" and line.get("event_uuid")
        if is_capture:
            event_uuid = line["event_uuid"]
            sequence = int(line.get("event_id") or 0)
        else:
            event_uuid = str(uuid.uuid5(UUID_NAMESPACE, "|".join(str(p) for p in (
                database, action, model, record_id, line.get("date"), line.get("message_id") or ""))))
            sequence = self._history_sequence(line.get("date"))

        root_model, root_id = self._root_of(line, model, record_id)
        return {
            "event_uuid": event_uuid,
            "source_sequence": sequence,
            "event_type": event_type,
            "source_model": model,
            "source_res_id": record_id,
            "source_res_name": line.get("record_name"),
            "root_key": "%s,%s" % (root_model, root_id),
            "source_user_login": line.get("user_login") or (line.get("user_id") and "uid %s" % line["user_id"]),
            "source_date": (line.get("date") or "")[:19] or False,
            "payload": json.dumps({
                "schema": 1,
                "source": {"db": database, "version": "17.0", "origin": "export_file",
                           "action": action, "user_id": line.get("user_id"),
                           "changes": line.get("changes") or []},
                "record": snapshot,
                "extra": extra,
            }, default=str),
            "origin": "import",
            "import_batch": batch,
        }, None

    @api.model
    def _history_sequence(self, date_string):
        try:
            moment = datetime.strptime((date_string or "")[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            return -HISTORY_SEQUENCE_OFFSET
        return int(moment.timestamp()) - HISTORY_SEQUENCE_OFFSET

    @api.model
    def _root_of(self, line, model, record_id):
        related = line.get("related") or {}
        params = line.get("params") or {}
        if model == "account.move":
            orders = params.get("sale_order_ids") or related.get("sale_order_ids") or []
            if orders:
                return "sale.order", orders[0]
            reversed_id = params.get("reversed_entry_id") or related.get("reversed_entry_id")
            if reversed_id:
                return "account.move", reversed_id
        return model, record_id
