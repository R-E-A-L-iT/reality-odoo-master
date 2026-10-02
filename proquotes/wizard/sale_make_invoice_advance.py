# -*- coding: utf-8 -*-

from odoo import models
from odoo.tools import frozendict


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _prepare_down_payment_lines_values(self, order):
        """Spread the down payment across lines that count in the quote total.

        Odoo 17 has no ``_get_down_payment_amount``. The 17.0 wizard
        (``addons/sale/wizard/sale_make_invoice_advance.py``) sets
        ``percentage = amount / 100`` or, for a fixed amount,
        ``fixed_amount / order.amount_total``, then multiplies every
        non-display, non-down-payment line by that share and groups the
        result by tax.

        ``_convert_to_tax_base_line_dict`` feeds ``price_unit`` and quantity
        into the tax engine. It does not use the stored subtotal, which
        proquotes zeros when ``selected == 'false'``. ``amount_total``
        already excludes those lines (``_proquotes_counts_in_totals``), so a
        percentage is applied to a larger base than the quote total and
        overcharges. A fixed amount is divided by the selected total and
        then spread across every line, including tax groups the customer
        did not select. ``_create_invoices`` forces the invoice total back
        to ``fixed_amount`` afterwards; the sale order lines stay inflated.

        This is that Odoo 17 method with the base lines limited to
        ``_proquotes_counts_in_totals`` (``selected == 'true'``).
        """
        self.ensure_one()

        if self.advance_payment_method == 'percentage':
            percentage = self.amount / 100
        else:
            percentage = self.fixed_amount / order.amount_total if order.amount_total else 1

        order_lines = order.order_line.filtered(
            lambda line: (
                not line.display_type
                and not line.is_downpayment
                and line._proquotes_counts_in_totals()
            )
        )
        base_downpayment_lines_values = self._prepare_base_downpayment_line_values(order)

        tax_base_line_dicts = [
            line._convert_to_tax_base_line_dict(
                analytic_distribution=line.analytic_distribution,
                handle_price_include=False,
            )
            for line in order_lines
        ]
        computed_taxes = self.env['account.tax']._compute_taxes(tax_base_line_dicts)
        down_payment_values = []
        for line, tax_repartition in computed_taxes['base_lines_to_update']:
            taxes = line['taxes'].flatten_taxes_hierarchy()
            fixed_taxes = taxes.filtered(lambda tax: tax.amount_type == 'fixed')
            down_payment_values.append([
                taxes - fixed_taxes,
                line['analytic_distribution'],
                tax_repartition['price_subtotal'],
            ])

        downpayment_line_map = {}
        analytic_map = {}
        for tax_id, analytic_distribution, price_subtotal in down_payment_values:
            grouping_key = frozendict({'tax_id': tuple(sorted(tax_id.ids))})
            downpayment_line_map.setdefault(grouping_key, {
                **base_downpayment_lines_values,
                **grouping_key,
                'product_uom_qty': 0.0,
                'price_unit': 0.0,
            })
            downpayment_line_map[grouping_key]['price_unit'] += price_subtotal
            if analytic_distribution:
                analytic_map.setdefault(grouping_key, [])
                analytic_map[grouping_key].append((price_subtotal, analytic_distribution))

        lines_values = []
        for key, line_vals in downpayment_line_map.items():
            # don't add line if price is 0 and prevent division by zero
            if order.currency_id.is_zero(line_vals['price_unit']):
                continue
            # weight analytic account distribution
            if analytic_map.get(key):
                line_analytic_distribution = {}
                for price_subtotal, account_distribution in analytic_map[key]:
                    for account, distribution in account_distribution.items():
                        line_analytic_distribution.setdefault(account, 0.0)
                        line_analytic_distribution[account] += (
                            price_subtotal / line_vals['price_unit'] * distribution
                        )
                line_vals['analytic_distribution'] = line_analytic_distribution
            # round price unit
            line_vals['price_unit'] = order.currency_id.round(line_vals['price_unit'] * percentage)
            lines_values.append(line_vals)

        return lines_values
