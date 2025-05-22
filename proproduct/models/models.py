from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_total')
    def _amount_all(self):
        super()._amount_all()

        for order in self:
            line_count = len(order.order_line.filtered(lambda l: l.display_type is False))
            extra = 100 * line_count
            order.amount_total += extra
            _logger.info("Added $%s to order %s (from %s lines)", extra, order.name or order.id, line_count)

