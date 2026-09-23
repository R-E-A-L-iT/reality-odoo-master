# -*- coding: utf-8 -*-
from odoo import api, models

MOVE_WATCHED = {
    "partner_id", "partner_shipping_id", "invoice_date", "invoice_date_due",
    "invoice_payment_term_id", "ref", "payment_reference", "journal_id",
    "invoice_line_ids", "narration", "fiscal_position_id", "currency_id",
    "invoice_user_id",
}
LINE_WATCHED = {
    "product_id", "quantity", "price_unit", "discount", "tax_ids", "name",
    "account_id", "product_uom_id", "sequence",
}
SYNCED_MOVE_TYPES = ("out_invoice", "out_refund")


def _move_root(move):
    return move.invoice_line_ids.sale_line_ids.order_id[:1] or move.reversed_entry_id or move


class AccountMove(models.Model):
    _inherit = "account.move"

    def _upgrade_sync_moves(self):
        return self.filtered(lambda m: m.move_type in SYNCED_MOVE_TYPES)

    def _upgrade_sync_enqueue(self, event_type, moves, extra=None):
        self.env["upgrade.sync.event"]._enqueue(event_type, moves, root=_move_root, extra=extra)

    def _upgrade_sync_in_creation_flow(self):
        """True while the invoice is being built by a flow replayed as a whole
        (invoice from sales order, reversal): no separate upsert is needed."""
        ctx = self.env.context
        return bool(ctx.get("upgrade_sync_invoice_from_sale") or ctx.get("upgrade_sync_reversal"))

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        if not self._upgrade_sync_in_creation_flow():
            self._upgrade_sync_enqueue("invoice.upsert", moves._upgrade_sync_moves())
        return moves

    def write(self, vals):
        res = super().write(vals)
        if MOVE_WATCHED.intersection(vals) and not self._upgrade_sync_in_creation_flow():
            self._upgrade_sync_enqueue(
                "invoice.upsert", self._upgrade_sync_moves().filtered(lambda m: m.state == "draft"))
        return res

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        moves = posted._upgrade_sync_moves().filtered(lambda m: m.state == "posted")
        # Snapshot the final draft content first, then the posting itself.
        self._upgrade_sync_enqueue("invoice.upsert", moves)
        self._upgrade_sync_enqueue("invoice.post", moves)
        return posted

    def button_cancel(self):
        res = super().button_cancel()
        self._upgrade_sync_enqueue("invoice.cancel", self._upgrade_sync_moves().filtered(lambda m: m.state == "cancel"))
        return res

    def button_draft(self):
        res = super().button_draft()
        self._upgrade_sync_enqueue("invoice.draft", self._upgrade_sync_moves().filtered(lambda m: m.state == "draft"))
        return res

    def _reverse_moves(self, default_values_list=None, cancel=False):
        reversed_moves = super(AccountMove, self.with_context(upgrade_sync_reversal=True))._reverse_moves(
            default_values_list=default_values_list, cancel=cancel)
        for reversal in reversed_moves._upgrade_sync_moves():
            self._upgrade_sync_enqueue(
                "invoice.reverse", reversal,
                extra={
                    "reversed_entry_id": reversal.reversed_entry_id.id,
                    "cancel": cancel,
                    "date": reversal.date and str(reversal.date),
                    "ref": reversal.ref or False,
                },
            )
        return reversed_moves


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def write(self, vals):
        res = super().write(vals)
        if LINE_WATCHED.intersection(vals) and not self.move_id._upgrade_sync_in_creation_flow():
            moves = self.move_id._upgrade_sync_moves().filtered(lambda m: m.state == "draft")
            moves._upgrade_sync_enqueue("invoice.upsert", moves)
        return res
