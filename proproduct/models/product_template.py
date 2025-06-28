# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    approve_financing = fields.Boolean("Approve Financing", default=False, help="If checked, the eCommerce page will show an APPROVE financing section.")
    show_add_to_cart = fields.Boolean("Show Add to Cart Button", default=False, help="If checked, the eCommerce page will show an Add To Cart button.")

