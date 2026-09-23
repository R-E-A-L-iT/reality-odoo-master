# -*- coding: utf-8 -*-
from odoo import api, models

PARTNER_WATCHED = {
    "name", "is_company", "parent_id", "type", "email", "phone", "mobile",
    "street", "street2", "city", "zip", "state_id", "country_id", "vat", "ref",
    "lang", "website", "function", "company_id", "user_id", "category_id",
    "property_payment_term_id", "property_product_pricelist", "active",
}


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        self.env["upgrade.sync.event"]._enqueue("partner.upsert", partners)
        return partners

    def write(self, vals):
        res = super().write(vals)
        if PARTNER_WATCHED.intersection(vals):
            self.env["upgrade.sync.event"]._enqueue("partner.upsert", self)
        return res
