# -*- coding: utf-8 -*-
"""Replay handlers: one ``_handle_<event_type>`` method per event type
(dots replaced by underscores), returning the Odoo 19 target record.

Handlers must be idempotent: replaying the same event twice must not create a
second document. They upsert the document to the Odoo 17 snapshot first, then
call the Odoo 19 business method (so proquotes & co. overrides run).

Custom modules add events without touching this file::

    class UpgradeSyncHandler(models.AbstractModel):
        _inherit = "upgrade.sync.handler"

        def _handle_rental_pickup(self, event, payload):
            order = self._upsert_sale_order(payload["record"])
            order.action_open_pickup()
            return order
"""
import logging

from odoo import api, models
from odoo.exceptions import UserError

from .exceptions import SyncDependencyMissing, SyncError

_logger = logging.getLogger(__name__)

REPLAY_CONTEXT = {
    "upgrade_sync_replay": True,
    # never let the replay push e-mails out immediately
    "mail_notify_force_send": False,
    "mail_auto_subscribe_no_notify": True,
}


class UpgradeSyncHandler(models.AbstractModel):
    _name = "upgrade.sync.handler"
    _description = "Upgrade Sync Replay Handlers"

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    @api.model
    def _get_handler_method(self, event_type):
        return getattr(self, "_handle_%s" % event_type.replace(".", "_"), None)

    @api.model
    def _dispatch(self, event, payload):
        handler = self.sudo().with_context(**REPLAY_CONTEXT)
        method = handler._get_handler_method(event.event_type)
        record_snap = payload.get("record") or {}
        company = self._company_of(record_snap)
        if company:
            handler = handler.with_company(company)
            method = handler._get_handler_method(event.event_type)
        return method(event, payload)

    @api.model
    def _company_of(self, snap):
        ref = snap.get("company_id")
        return self._resolver._resolve(ref, required=False) if ref else None

    @property
    def _resolver(self):
        return self.env["upgrade.sync.resolver"]

    @property
    def _transformer(self):
        return self.env["upgrade.sync.transformer"]

    @property
    def _mapping(self):
        return self.env["upgrade.sync.mapping"]

    @api.model
    def _mapped(self, source_model, source_id):
        return self._mapping._lookup(source_model, source_id)

    @api.model
    def _require(self, snap):
        """Target record of a snapshot, or raise dependency missing."""
        return self._resolver._resolve(_self_ref(snap), required=True)

    # ------------------------------------------------------------------
    # Contacts / products
    # ------------------------------------------------------------------
    @api.model
    def _upsert_simple(self, model, snap, vals):
        record = self._resolver._resolve(_self_ref(snap), required=False) \
            if model not in ("res.partner",) else self._partner_lookup(snap)
        if record:
            record.write(vals)
        else:
            record = self.env[model].create(vals)
            self._mapping._set(snap["model"], snap["id"], record, "created", snap.get("name"))
        return record

    @api.model
    def _partner_lookup(self, snap):
        # a full partner snapshot is authoritative: no "created from reference"
        ref = _self_ref(snap)
        record = self._mapping._lookup("res.partner", snap["id"])
        if record:
            return record
        Model = self.env["res.partner"].with_context(active_test=False)
        resolver = self._resolver
        record = resolver._match_by_seed_id(Model, ref) or resolver._match_by_keys(Model, ref)
        if record:
            self._mapping._set("res.partner", snap["id"], record, "seed_id", snap.get("name"))
        return record

    @api.model
    def _handle_partner_upsert(self, event, payload):
        snap = payload["record"]
        return self._upsert_simple("res.partner", snap, self._transformer._partner_vals(snap))

    @api.model
    def _handle_product_upsert(self, event, payload):
        snap = payload["record"]
        template = self._upsert_simple("product.template", snap, self._transformer._product_template_vals(snap))
        # map variants by position (single-variant products are the common case)
        variants = template.product_variant_ids
        for ref, variant in zip(snap.get("variants") or [], variants):
            self._mapping._set("product.product", ref["id"], variant, "created", ref.get("name"))
        return template

    # ------------------------------------------------------------------
    # CRM
    # ------------------------------------------------------------------
    @api.model
    def _upsert_lead(self, snap):
        vals = self._transformer._lead_vals(snap)
        lead = self._resolver._resolve(_self_ref(snap), required=False)
        if lead:
            lead.write(vals)
        else:
            stage = self._resolver._resolve(snap.get("stage_id"), required=False)
            if stage:
                vals["stage_id"] = stage.id
            lead = self.env["crm.lead"].create(vals)
            self._mapping._set("crm.lead", snap["id"], lead, "created", snap.get("name"))
        return lead

    @api.model
    def _handle_lead_upsert(self, event, payload):
        return self._upsert_lead(payload["record"])

    @api.model
    def _handle_lead_stage(self, event, payload):
        snap = payload["record"]
        lead = self._upsert_lead(snap)
        stage = self._resolver._resolve(snap.get("stage_id"))
        if lead.stage_id != stage:
            lead.write({"stage_id": stage.id})
        return lead

    @api.model
    def _handle_lead_won(self, event, payload):
        lead = self._upsert_lead(payload["record"])
        if lead.won_status != "won":
            lead.action_set_won()
        return lead

    @api.model
    def _handle_lead_lost(self, event, payload):
        snap = payload["record"]
        lead = self._upsert_lead(snap)
        if lead.active:
            reason = self._resolver._resolve(snap.get("lost_reason_id"), required=False)
            lead.action_set_lost(**({"lost_reason_id": reason.id} if reason else {}))
        return lead

    # ------------------------------------------------------------------
    # Sales
    # ------------------------------------------------------------------
    @api.model
    def _upsert_sale_order(self, snap):
        """Create or align the Odoo 19 order with the Odoo 17 snapshot."""
        transformer = self._transformer
        order = self._resolver._resolve(_self_ref(snap), required=False)
        header = transformer._sale_order_vals(snap)
        lines = transformer._sale_lines(snap)
        if not order:
            header["order_line"] = [(0, 0, vals) for (_src, vals) in lines]
            order = self.env["sale.order"].create(header)
            self._mapping._set("sale.order", snap["id"], order, "created", snap.get("name"))
            created_lines = order.order_line.filtered(lambda l: not l.x_is_rental_kit_component) \
                .sorted(lambda l: (l.sequence, l.id))
            if len(created_lines) != len(lines):
                raise SyncError("Order %s: %s lines replayed, %s created in Odoo 19." % (
                    snap.get("name"), len(lines), len(created_lines)))
            for (src, _vals), line in zip(lines, created_lines):
                self._mapping._set("sale.order.line", src["id"], line, "created", src.get("name"))
        else:
            if order.state in ("draft", "sent"):
                order.write(header)
            else:
                # confirmed orders: only non-structural header fields
                order.write({k: v for k, v in header.items() if k in (
                    "client_order_ref", "origin", "note", "commitment_date", "user_id", "team_id")})
            self._sync_sale_lines(order, lines)
        self._enforce_line_quantities(order, lines)
        return order

    @api.model
    def _target_sale_line(self, order, src):
        line = self._mapped("sale.order.line", src["id"])
        if line and line.order_id == order:
            return line
        # upgraded copy: same id on the same order is the same line
        line = self.env["sale.order.line"].browse(src["id"]).exists()
        if line and line.order_id == order:
            self._mapping._set("sale.order.line", src["id"], line, "seed_id", src.get("name"))
            return line
        return None

    @api.model
    def _sync_sale_lines(self, order, lines):
        seen = self.env["sale.order.line"]
        editable = order.state in ("draft", "sent")
        for src, vals in lines:
            line = self._target_sale_line(order, src)
            if line:
                if editable or not line.display_type:
                    changed = _changed(line, vals)
                    changed.pop("display_type", None)
                    line.write(changed)
            else:
                line = self.env["sale.order.line"].create(dict(vals, order_id=order.id))
                self._mapping._set("sale.order.line", src["id"], line, "created", src.get("name"))
            seen |= line
        obsolete = order.order_line.filtered(lambda l: not l.x_is_rental_kit_component) - seen
        if obsolete:
            if editable:
                obsolete.unlink()
            else:
                # Odoo does not allow deleting lines of a confirmed order that
                # are delivered/invoiced; Odoo 17 would have refused too.
                obsolete.filtered(lambda l: not l.display_type and not l.qty_invoiced and not l.qty_delivered) \
                    .write({"product_uom_qty": 0})

    @api.model
    def _enforce_line_quantities(self, order, lines):
        """The proquotes selection cascade (optional / single choice) may reset
        member quantities while sections are written: re-apply the Odoo 17
        selection so Odoo 19 ends in the same state."""
        for src, vals in lines:
            if vals.get("display_type"):
                continue
            line = self._target_sale_line(order, src)
            if line and line.product_uom_qty != vals["product_uom_qty"] and not line.qty_invoiced:
                line.with_context(_single_choice_no_cascade=True).write({
                    "product_uom_qty": vals["product_uom_qty"],
                    "x_preset_qty": vals["x_preset_qty"],
                })

    @api.model
    def _handle_sale_upsert(self, event, payload):
        return self._upsert_sale_order(payload["record"])

    @api.model
    def _handle_sale_sent(self, event, payload):
        order = self._upsert_sale_order(payload["record"])
        if order.state == "draft":
            # "Mark as sent" semantic: no e-mail leaves the test instance
            order.action_quotation_sent()
        return order

    @api.model
    def _handle_sale_confirm(self, event, payload):
        order = self._upsert_sale_order(payload["record"])
        if order.state in ("draft", "sent"):
            order.action_confirm()
        if order.state != "sale":
            raise UserError("Order %s is in state '%s' after action_confirm()." % (order.name, order.state))
        return order

    @api.model
    def _handle_sale_cancel(self, event, payload):
        order = self._require(payload["record"])
        if order.state != "cancel":
            order._action_cancel()
        return order

    @api.model
    def _handle_sale_draft(self, event, payload):
        order = self._require(payload["record"])
        if order.state == "cancel":
            order.action_draft()
        return order

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------
    @api.model
    def _handle_invoice_create_from_sale(self, event, payload):
        snap = payload["record"]
        move = self._mapped("account.move", snap["id"])
        if not move:
            move = self._resolver._match_by_seed_id(self.env["account.move"], _self_ref(snap))
            if move:
                self._mapping._set("account.move", snap["id"], move, "seed_id", snap.get("name"))
        if not move:
            orders = self._resolver._resolve_many(snap.get("sale_order_ids"))
            if not orders:
                raise SyncError("Invoice %s: no sales order in the snapshot." % snap.get("name"))
            extra = payload.get("extra") or {}
            before = orders.invoice_ids
            moves = orders._create_invoices(grouped=extra.get("grouped", False), final=extra.get("final", False))
            moves = (moves | orders.invoice_ids) - before
            if not moves:
                raise UserError("Odoo 19 created no invoice for %s (nothing to invoice)." %
                                ", ".join(orders.mapped("name")))
            move = self._pick_invoice_for_snapshot(moves, snap)
            self._mapping._set("account.move", snap["id"], move, "created", snap.get("name"))
        self._align_move(move, snap)
        return move

    @api.model
    def _pick_invoice_for_snapshot(self, moves, snap):
        if len(moves) == 1:
            return moves
        wanted = {self._mapped("sale.order.line", sl["id"]).id
                  for line in snap.get("lines") or [] for sl in line.get("sale_line_ids") or []} - {None}
        for move in moves:
            if wanted & set(move.invoice_line_ids.sale_line_ids.ids):
                return move
        return moves[:1]

    @api.model
    def _target_move_line(self, move, src):
        line = self._mapped("account.move.line", src["id"])
        if line and line.move_id == move:
            return line
        for sale_ref in src.get("sale_line_ids") or []:
            sale_line = self._mapped("sale.order.line", sale_ref["id"])
            if sale_line:
                candidates = move.invoice_line_ids.filtered(lambda l: sale_line in l.sale_line_ids)
                if len(candidates) == 1:
                    self._mapping._set("account.move.line", src["id"], candidates, "business_key", src.get("name"))
                    return candidates
        line = self.env["account.move.line"].browse(src["id"]).exists()
        if line and line.move_id == move:
            self._mapping._set("account.move.line", src["id"], line, "seed_id", src.get("name"))
            return line
        return None

    @api.model
    def _align_move(self, move, snap):
        """Align a draft Odoo 19 invoice with the Odoo 17 snapshot."""
        if move.state != "draft":
            return move
        transformer = self._transformer
        move.write(_changed(move, transformer._move_header_update_vals(snap)))
        seen = self.env["account.move.line"]
        commands = []
        for src, vals in transformer._move_lines(snap):
            line = self._target_move_line(move, src)
            if not line and vals["display_type"] != "product":
                # sections / notes (proquotes adds its own): match by text
                line = (move.invoice_line_ids - seen).filtered(
                    lambda l: l.display_type == vals["display_type"] and (l.name or "") == (vals["name"] or ""))[:1]
            if line:
                changed = _changed(line, vals)
                changed.pop("display_type", None)
                if changed:
                    commands.append((1, line.id, changed))
                seen |= line
            else:
                commands.append((0, 0, vals))
        obsolete = move.invoice_line_ids - seen
        commands += [(2, line.id) for line in obsolete]
        if commands:
            move.write({"invoice_line_ids": commands})
        return move

    @api.model
    def _handle_invoice_upsert(self, event, payload):
        snap = payload["record"]
        move = self._resolver._resolve(_self_ref(snap), required=False)
        if not move:
            if snap.get("sale_order_ids"):
                # built from a sales order outside _create_invoices (down payment
                # wizard, ...): the create_from_sale event must come first.
                raise SyncDependencyMissing(
                    _self_ref(snap), "Invoice %s comes from a sales order but was not created by a "
                                     "create_from_sale event (down payment?)" % snap.get("name"))
            vals = self._transformer._move_vals(snap)
            vals["invoice_line_ids"] = [(0, 0, v) for (_src, v) in self._transformer._move_lines(snap)]
            move = self.env["account.move"].create(vals)
            self._mapping._set("account.move", snap["id"], move, "created", snap.get("name"))
            for src, line in zip(
                    [s for s, _v in self._transformer._move_lines(snap)],
                    move.invoice_line_ids.sorted(lambda l: (l.sequence, l.id))):
                self._mapping._set("account.move.line", src["id"], line, "created", src.get("name"))
            return move
        return self._align_move(move, snap)

    @api.model
    def _handle_invoice_post(self, event, payload):
        snap = payload["record"]
        move = self._require(snap)
        if move.state == "draft":
            self._align_move(move, snap)
            move.action_post()
        if move.state != "posted":
            raise UserError("Invoice %s is in state '%s' after action_post()." % (move.display_name, move.state))
        return move

    @api.model
    def _handle_invoice_cancel(self, event, payload):
        move = self._require(payload["record"])
        if move.state == "posted":
            move.button_draft()
        if move.state != "cancel":
            move.button_cancel()
        return move

    @api.model
    def _handle_invoice_draft(self, event, payload):
        move = self._require(payload["record"])
        if move.state != "draft":
            move.button_draft()
        return move

    @api.model
    def _handle_invoice_reverse(self, event, payload):
        snap = payload["record"]
        extra = payload.get("extra") or {}
        reversal = self._mapped("account.move", snap["id"])
        if not reversal:
            origin = self._resolver._resolve(snap.get("reversed_entry_id"))
            reversal = origin._reverse_moves(
                default_values_list=[{
                    "date": extra.get("date") or snap.get("date"),
                    "invoice_date": snap.get("invoice_date") or extra.get("date"),
                    "ref": extra.get("ref") or snap.get("ref"),
                }],
                cancel=bool(extra.get("cancel")),
            )
            self._mapping._set("account.move", snap["id"], reversal, "created", snap.get("name"))
        return self._align_move(reversal, snap)


def _self_ref(snap):
    """Reference to the snapshot's own record (same shape as an Odoo 17 ref)."""
    keys = {k: snap.get(k) or None for k in ("email", "vat", "ref", "default_code", "barcode")}
    keys.update({"name": snap.get("name"), "is_company": snap.get("is_company")})
    return {
        "model": snap["model"],
        "id": snap["id"],
        "name": snap.get("name"),
        "create_date": snap.get("create_date"),
        "keys": keys,
    }


def _changed(record, vals):
    """Only the values that differ (avoids useless writes/recomputations)."""
    changed = {}
    for fname, value in vals.items():
        field = record._fields.get(fname)
        if field is None:
            continue
        current = record[fname]
        if field.type in ("many2one",):
            if (current.id or False) != (value or False):
                changed[fname] = value
        elif field.type == "many2many":
            if isinstance(value, list) and value and value[0][0] == 6 and set(current.ids) == set(value[0][2]):
                continue
            changed[fname] = value
        elif field.type == "float":
            if abs((current or 0.0) - (value or 0.0)) > 1e-6:
                changed[fname] = value
        elif (current or False) != (value or False):
            changed[fname] = value
    return changed
