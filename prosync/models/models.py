from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    sku = fields.Char(string="SKU", readonly=False, index=True, help="Stock Keeping Unit")
    discontinued = fields.Boolean(string="Discontinued", default=False, index=True, help="If checked, this product has been discontinued by the manufacturer but remains in the system for backward compatibility.")

class ResPartner(models.Model):
    _inherit = "res.partner"

    pricelist_id = fields.Many2one("product.pricelist", "Pricelist_Sync")

    @api.depends("pricelist_id")
    def _compute_product_pricelist(self):
        for p in self:
            p.property_product_pricelist = p.pricelist_id