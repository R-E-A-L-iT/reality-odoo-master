from odoo import fields, models


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # Selected delivery carrier for this product line (set by customer at e-commerce checkout)
    carrier_id = fields.Many2one(
        'delivery.carrier',
        string='Delivery Method',
        copy=False,
    )

    # On delivery (is_delivery=True) lines: which product lines does this charge cover?
    source_line_ids = fields.Many2many(
        'sale.order.line',
        relation='sale_delivery_source_rel',
        column1='delivery_line_id',
        column2='source_line_id',
        string='Source Product Lines',
        copy=False,
    )
