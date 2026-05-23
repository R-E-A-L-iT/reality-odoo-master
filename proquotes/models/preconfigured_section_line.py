# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PreconfiguredSectionLine(models.Model):
    _name = 'preconfigured.section.line'
    _description = 'Preconfigured Section Line'
    _rec_name = 'product_name'

    section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_name = fields.Char(string='Name')
    optional = fields.Boolean(string='Optional')
    selected = fields.Boolean(string='Selected', default=True)
    quantity_locked = fields.Boolean(string='Quantity Locked')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Disc. (%)', default=0.0)

    @api.onchange('product_id')
    def _onchange_product_name(self):
        if self.product_id:
            self.product_name = self.product_id.name
            self.price_unit = self.product_id.lst_price
        else:
            self.product_name = False
            self.price_unit = 0.0
