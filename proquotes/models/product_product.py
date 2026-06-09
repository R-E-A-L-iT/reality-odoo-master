# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class products(models.Model):
    _inherit = "product.product"
    

    def get_kit_description_text(self):
        bom = self.env['mrp.bom'].sudo().search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('type', '=', 'phantom'),
        ], limit=1)
        if not bom or not bom.bom_line_ids:
            return ''
        lines = []
        for line in bom.sudo().bom_line_ids:
            qty = int(line.product_qty) if line.product_qty == int(line.product_qty) else line.product_qty
            sku = line.product_id.product_tmpl_id.sku
            name = line.product_id.name
            part = f"{qty}x {sku} - {name}" if sku else f"{qty}x {name}"
            lines.append(part)
        return '\n'.join(lines)
        
    def get_product_multiline_description_sale(self):
        bom = self.env['mrp.bom'].search([
            ('product_tmpl_id', '=', self.product_tmpl_id.id),
            ('type', '=', 'phantom'),
        ], limit=1)
        if bom and bom.bom_line_ids:
            lines = [
                f"{int(line.product_qty) if line.product_qty == int(line.product_qty) else line.product_qty} \u00d7 {line.product_id.name}"
                for line in bom.bom_line_ids
            ]
            return "<br/>".join(lines)
        if self.description_sale:
            return self.description_sale
        return "<span></span>"

class ProductProduct(models.Model):
    _inherit = "product.product"

    price = fields.Float(
        'Price', compute='_compute_product_price',
        digits='Product Price', inverse='_set_product_price')

    @api.depends_context('pricelist', 'partner', 'quantity', 'uom', 'date', 'no_variant_attributes_price_extra')
    def _compute_product_price(self):
        prices = {}
        pricelist_id_or_name = self._context.get('pricelist')
        if pricelist_id_or_name:
            pricelist = None
            partner = self.env.context.get('partner', False)
            quantity = self.env.context.get('quantity', 1.0)

            # Support context pricelists specified as list, display_name or ID for compatibility
            if isinstance(pricelist_id_or_name, list):
                pricelist_id_or_name = pricelist_id_or_name[0]
            if isinstance(pricelist_id_or_name, str):
                pricelist_name_search = self.env['product.pricelist'].name_search(pricelist_id_or_name, operator='=',
                                                                                  limit=1)
                if pricelist_name_search:
                    pricelist = self.env['product.pricelist'].browse([pricelist_name_search[0][0]])
            elif isinstance(pricelist_id_or_name, int):
                pricelist = self.env['product.pricelist'].browse(pricelist_id_or_name)

            if pricelist:
                quantities = [quantity] * len(self)
                partners = [partner] * len(self)
                prices = pricelist.get_products_price(self, quantities, partners)

        for product in self:
            product.price = prices.get(product.id, 0.0)

    def _set_product_price(self):
        for product in self:
            if self._context.get('uom'):
                value = self.env['uom.uom'].browse(self._context['uom'])._compute_price(product.price, product.uom_id)
            else:
                value = product.price
            value -= product.price_extra
            product.write({'list_price': value})