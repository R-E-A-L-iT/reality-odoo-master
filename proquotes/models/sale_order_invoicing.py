# -*- coding: utf-8 -*-

from odoo import api, models
from odoo.tools import float_compare, float_is_zero


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _proquotes_is_unselected_product_line(self):
        """Product line the customer did not select.

        Display lines are never unselected. ``selected`` is the string
        ``'true'`` or ``'false'`` (both truthy), so this uses the same
        rule as quote totals.
        """
        self.ensure_one()
        return not self.display_type and not self._proquotes_counts_in_totals()

    @api.depends('selected')
    def _compute_qty_to_invoice(self):
        super()._compute_qty_to_invoice()
        for line in self:
            if line._proquotes_is_unselected_product_line():
                line.qty_to_invoice = 0.0

    @api.depends('selected')
    def _compute_untaxed_amount_to_invoice(self):
        super()._compute_untaxed_amount_to_invoice()
        for line in self:
            if line._proquotes_is_unselected_product_line():
                line.untaxed_amount_to_invoice = 0.0

    @api.depends('selected')
    def _compute_invoice_status(self):
        super()._compute_invoice_status()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for line in self:
            if line.state != 'sale' or line.is_downpayment:
                continue
            if not line._proquotes_is_unselected_product_line():
                continue
            has_invoiced_qty = not float_is_zero(line.qty_invoiced, precision_digits=precision)
            covered = float_compare(
                line.qty_invoiced,
                line.product_uom_qty,
                precision_digits=precision,
            ) >= 0
            if has_invoiced_qty and covered:
                line.invoice_status = 'invoiced'
            else:
                line.invoice_status = 'no'


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.selected')
    def _compute_invoice_status(self):
        """Recompute from selected lines when the order has unselected ones.

        Core marks the order ``no`` when any non-display line is ``no``.
        Unselected lines are ``no`` (or a stale ``to invoice``), which would
        hide fully invoiced orders. Orders with no unselected product line
        keep the core result.
        """
        super()._compute_invoice_status()
        for order in self:
            if order.state != 'sale':
                continue
            if not any(
                line._proquotes_is_unselected_product_line()
                for line in order.order_line
            ):
                continue
            counted = order.order_line.filtered(
                lambda line: (
                    not line.display_type
                    and not line.is_downpayment
                    and line._proquotes_counts_in_totals()
                )
            )
            statuses = [line.invoice_status for line in counted]
            if any(status == 'to invoice' for status in statuses):
                if any(status == 'no' for status in statuses):
                    invoiceable = counted.filtered(
                        lambda line: line.invoice_status == 'to invoice'
                    )
                    special = invoiceable.filtered(
                        lambda line: not line._can_be_invoiced_alone()
                    )
                    order.invoice_status = 'no' if invoiceable == special else 'to invoice'
                else:
                    order.invoice_status = 'to invoice'
            elif statuses and all(status == 'invoiced' for status in statuses):
                order.invoice_status = 'invoiced'
            elif statuses and all(status in ('invoiced', 'upselling') for status in statuses):
                order.invoice_status = 'upselling'
            else:
                order.invoice_status = 'no'

    def _get_invoiceable_lines(self, final=False):
        """Drop unselected product lines, including stale stored quantities.

        The filter reads ``selected`` live, so existing orders are protected
        before their stored ``qty_to_invoice`` is recomputed. A section stays
        only when a kept non-section, non-down-payment line follows it.
        Notes and down payments stay as core returned them.
        """
        lines = super()._get_invoiceable_lines(final=final)
        if not any(line._proquotes_is_unselected_product_line() for line in lines):
            return lines

        kept_ids = []
        pending_section = None
        for line in lines:
            if line.display_type == 'line_section':
                pending_section = line
                continue
            if line._proquotes_is_unselected_product_line():
                continue
            if pending_section and not line.is_downpayment:
                kept_ids.append(pending_section.id)
                pending_section = None
            kept_ids.append(line.id)
        return self.env['sale.order.line'].browse(kept_ids)
