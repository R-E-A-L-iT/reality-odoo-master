# -*- coding: utf-8 -*-

from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sku = fields.Char(string="SKU", readonly=False, index=True, help="Stock Keeping Unit")
    discontinued = fields.Boolean(string="Discontinued", default=False, index=True, help="If checked, this product has been discontinued by the manufacturer but remains in the system for backward compatibility.")
