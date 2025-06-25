# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductBundleInstance(models.Model):
    _name = 'product.bundle.instance'
    _description = 'Product Bundle Instance'

    name = fields.Char(string='Lot/Serial Number', required=True, help="Name of the bundle instance")
    bundle_id = fields.Many2one('product.bundle', string='Bundle', required=True, ondelete='cascade')
    product_qty = fields.Float(string='On Hand Quantity', default=0.0, readonly=True)
    ref = fields.Char(string='Internal Reference', help="Reference for the bundle instance")
    company_id = fields.Many2one('res.company', string='Company', required=True, default=lambda self: self.env.company)
    owner = fields.Many2one('res.partner', string='Owner', help="Owner of the bundle instance")
    sku = fields.Char(string='SKU', related='bundle_id.sku', readonly=True, help="SKU of the bundle")
    expire = fields.Date(string='Expiration Date', help="Expiration date of the bundle")

    lot_lines = fields.One2many(
        'stock.lot',
        'bundle_instance_id',
        string="Subproducts"
    )
