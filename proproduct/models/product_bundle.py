# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductBundleLine(models.Model):
    _name = 'product.bundle.line'
    _description = 'Product Bundle Line'

    bundle_id = fields.Many2one('product.bundle', string='Bundle', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.template', string='Product', required=True)
    # product_description = fields.Text(string='Sales Description', related='product_id.description_sale', store=True)
    quantity = fields.Float(string='Quantity', default=1.0)

    product_description = fields.Text(string='Description', compute='_compute_product_description', store=True)

    @api.depends('product_id')
    def _compute_product_description(self):
        for line in self:
            if line.product_id:
                line.product_description = line.product_id.name or ''
            else:
                line.product_description = ''


class ProductBundle(models.Model):
    _name = 'product.bundle'
    _description = 'Product Bundle'

    name = fields.Char(string='Bundle Name', required=True)
    sku = fields.Char(string='SKU')
    product_lines = fields.One2many('product.bundle.line', 'bundle_id', string='Products')
