# -*- coding: utf-8 -*-
from odoo import api, models

PRODUCT_WATCHED = {
    "name", "default_code", "barcode", "detailed_type", "type", "list_price",
    "standard_price", "sale_ok", "purchase_ok", "rent_ok", "invoice_policy",
    "categ_id", "uom_id", "uom_po_id", "taxes_id", "supplier_taxes_id",
    "description_sale", "company_id", "active",
}


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        self.env["upgrade.sync.event"]._enqueue("product.upsert", templates)
        return templates

    def write(self, vals):
        res = super().write(vals)
        if PRODUCT_WATCHED.intersection(vals):
            self.env["upgrade.sync.event"]._enqueue("product.upsert", self)
        return res
