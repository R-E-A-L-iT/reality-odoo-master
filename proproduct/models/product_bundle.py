# -*- coding: utf-8 -*-

from odoo import models, fields

class ProductBundleLine(models.Model):
    _name = 'product.bundle.line'
    _description = 'Product Bundle Line'

    bundle_id = fields.Many2one('product.bundle', string='Bundle', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.template', string='Product', required=True)
    product_description = fields.Char(string='Description', related='product_id.description', store=True)
    quantity = fields.Float(string='Quantity', default=1.0)

class ProductBundle(models.Model):
    _name = 'product.bundle'
    _description = 'Product Bundle'

    name = fields.Char(string='Bundle Name', required=True)
    sku = fields.Char(string='SKU')
    product_lines = fields.One2many('product.bundle.line', 'bundle_id', string='Products')
