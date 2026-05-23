# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo import models, fields


class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    header_id = fields.Many2one('header.footer', string="Default Header")

    def _prepare_sale_order_line_values(self, order, line, **kwargs):
        vals = super()._prepare_sale_order_line_values(order, line, **kwargs)
        if hasattr(line, 'discount') and line.discount:
            vals['discount'] = line.discount
        return vals

    def _prepare_sale_order_optional_line_values(self, order, option_line, **kwargs):
        vals = super()._prepare_sale_order_optional_line_values(order, option_line, **kwargs)
        if hasattr(option_line, 'discount') and option_line.discount:
            vals['discount'] = option_line.discount
        return vals
