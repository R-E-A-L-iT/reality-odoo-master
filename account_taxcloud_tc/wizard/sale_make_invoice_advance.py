# copyright 2025 Sodexis
# license OPL-1 (see license file for full copyright and licensing details).

from odoo import models


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = 'sale.advance.payment.inv'

    def _prepare_down_payment_lines_values(self, order):
        lines_values, accounts = super()._prepare_down_payment_lines_values(order)
        
        zero_tax = self.env['account.tax'].search([
            ('amount', '=', 0),
            ('type_tax_use', '=', 'sale'),
            ('company_id', '=', order.company_id.id),
        ], limit=1)

        # Ensure down payment lines never get taxes
        for line_vals in lines_values:
            if line_vals.get("is_downpayment", True):
                if zero_tax:
                    # Set tax_id to 0% tax
                    line_vals["tax_id"] = [(6, 0, zero_tax.ids)]
                else:
                    # fallback → no tax if no 0% tax defined
                    line_vals["tax_id"] = [(6, 0, [])]

        return lines_values, accounts