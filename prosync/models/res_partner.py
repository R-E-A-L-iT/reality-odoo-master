# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = "res.partner"

    pricelist_id = fields.Many2one("product.pricelist", "Pricelist_Sync")

    @api.depends("pricelist_id")
    def _compute_product_pricelist(self):
        for p in self:
            p.property_product_pricelist = p.pricelist_id
