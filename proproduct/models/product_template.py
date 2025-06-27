# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    approve_financing = fields.Boolean("Approve Financing", default=False, help="If checked, the eCommerce page will show an APPROVE financing section.")

    is_us = fields.Boolean(string='US')
    is_ca = fields.Boolean(string='CA')

    def action_is_us_toggle(self):
        self.is_us = not self.is_us

    def action_is_ca_toggle(self):
        self.is_ca = not self.is_ca