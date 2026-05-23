# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo import models, fields


class renewal_entry(models.Model):
    _name = 'renewal.entry'
    _description = 'Hold order information for renewal.map'
    _rec_name = 'product_id'
    _order = 'order'
    order = fields.Integer(string="Order", required=True)
    product_id = fields.Many2one(
        'product.product', string="Product", required="True")
    map_id = fields.Many2one(comodel_name='renewal.map')
    selected = fields.Boolean(string="Option Selected",
                              default=False)
