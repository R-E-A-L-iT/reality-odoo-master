# -*- coding: utf-8 -*-

from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    approve_financing = fields.Boolean("Approve Financing", default=False, help="If checked, the eCommerce page will show an APPROVE financing section.")
    show_add_to_cart = fields.Boolean("Show Add to Cart Button", default=False, help="If checked, the eCommerce page will show an Add To Cart button.")
    rental_behaviour_on_store = fields.Boolean(
        string="Rental behaviour on store",
        default=False,
        help="If enabled, rental-specific elements will be shown on the website product page."
    )

    is_us = fields.Boolean(string='Is Published in US')
    is_ca = fields.Boolean(string='Is Published in CA')

    def action_is_us_toggle(self):
        self.is_us = not self.is_us

    def action_is_ca_toggle(self):
        self.is_ca = not self.is_ca
