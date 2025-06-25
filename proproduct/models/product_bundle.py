# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductBundleLine(models.Model):
    _name = 'product.bundle.line'
    _description = 'Product Bundle Line'

    bundle_id = fields.Many2one('product.bundle', string='Bundle', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.template', string='Product', required=True)
    quantity = fields.Float(string='Quantity', default=1.0)


class ProductBundle(models.Model):
    _name = 'product.bundle'
    _description = 'Product Bundle'

    name = fields.Char(string='Bundle Name', required=True)
    sku = fields.Char(string='SKU')
    product_lines = fields.One2many('product.bundle.line', 'bundle_id', string='Products')

    price_cad = fields.Monetary(string='Price (CAD)', currency_field='currency_id_cad')
    price_usd = fields.Monetary(string='Price (USD)', currency_field='currency_id_usd')
    rental_price_cad = fields.Monetary(string='Rental Price (CAD)', currency_field='currency_id_cad')
    rental_price_usd = fields.Monetary(string='Rental Price (USD)', currency_field='currency_id_usd')

    def _get_currency_cad(self):
        try:
            return self.env.ref('base.CAD')
        except ValueError:
            return None

    def _get_currency_usd(self):
        try:
            return self.env.ref('base.USD')
        except ValueError:
            return None


    currency_id_cad = fields.Many2one(
        'res.currency', string='CAD Currency',
        default=_get_currency_cad, readonly=True
    )
    currency_id_usd = fields.Many2one(
        'res.currency', string='USD Currency',
        default=_get_currency_usd, readonly=True
    )

