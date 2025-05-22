from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_total')
    def _amount_all(self):
        super()._amount_all()

        for order in self:
            
            # Add $100 per line (excluding section/note lines)
            line_count = len(order.order_line.filtered(lambda l: l.display_type is False))
            order.amount_total += 100 * line_count
