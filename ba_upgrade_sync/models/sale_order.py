# -*- coding: utf-8 -*-
from odoo import api, models

ORDER_WATCHED = {
    "partner_id", "partner_invoice_id", "partner_shipping_id", "date_order",
    "validity_date", "commitment_date", "pricelist_id", "payment_term_id",
    "fiscal_position_id", "user_id", "team_id", "opportunity_id",
    "sale_order_template_id", "client_order_ref", "origin", "note",
    "order_line", "is_rental_order", "rental_start_date", "rental_return_date",
}
LINE_WATCHED = {
    "product_id", "product_uom_qty", "product_uom", "price_unit", "discount",
    "tax_id", "name", "sequence", "display_type", "selected", "sectionSelected",
    "special", "optional", "quantityLocked", "ba_kit_description",
}


def _order_root(order):
    return order


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        self.env["upgrade.sync.event"]._enqueue("sale.upsert", orders)
        return orders

    def write(self, vals):
        before_draft = self.filtered(lambda o: o.state == "draft") if vals.get("state") == "sent" else self.browse()
        res = super().write(vals)
        Event = self.env["upgrade.sync.event"]
        if ORDER_WATCHED.intersection(vals):
            Event._enqueue("sale.upsert", self)
        if before_draft:
            # Covers both "Mark as sent" and the mail composer (mark_so_as_sent).
            Event._enqueue("sale.sent", before_draft)
        return res

    def action_confirm(self):
        res = super().action_confirm()
        Event = self.env["upgrade.sync.event"]
        confirmed = self.filtered(lambda o: o.state == "sale")
        # Snapshot first so the receiver has the exact lines that were confirmed.
        Event._enqueue("sale.upsert", confirmed)
        Event._enqueue("sale.confirm", confirmed)
        return res

    def _action_cancel(self):
        res = super()._action_cancel()
        self.env["upgrade.sync.event"]._enqueue("sale.cancel", self.filtered(lambda o: o.state == "cancel"))
        return res

    def action_draft(self):
        res = super().action_draft()
        self.env["upgrade.sync.event"]._enqueue("sale.draft", self.filtered(lambda o: o.state == "draft"))
        return res

    def _create_invoices(self, grouped=False, final=False, date=None):
        # Invoices created here are replayed by "invoice.create_from_sale";
        # do not also capture them as stand-alone "invoice.upsert".
        orders = self.with_context(upgrade_sync_invoice_from_sale=True)
        moves = super(SaleOrder, orders)._create_invoices(grouped=grouped, final=final, date=date)
        if moves:
            self.env["upgrade.sync.event"]._enqueue(
                "invoice.create_from_sale", moves,
                root=lambda m: m.invoice_line_ids.sale_line_ids.order_id[:1],
                extra=lambda m: {
                    "sale_order_ids": m.invoice_line_ids.sale_line_ids.order_id.ids,
                    "grouped": grouped,
                    "final": final,
                    "date": date and str(date),
                },
            )
        return moves


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get("upgrade_sync_invoice_from_sale"):
            self.env["upgrade.sync.event"]._enqueue("sale.upsert", lines.order_id)
        return lines

    def write(self, vals):
        res = super().write(vals)
        if LINE_WATCHED.intersection(vals):
            self.env["upgrade.sync.event"]._enqueue("sale.upsert", self.order_id)
        return res

    def unlink(self):
        orders = self.order_id
        res = super().unlink()
        self.env["upgrade.sync.event"]._enqueue("sale.upsert", orders.exists())
        return res
