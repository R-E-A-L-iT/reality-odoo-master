from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    sku = fields.Char(string="SKU", readonly=False, index=True, help="Stock Keeping Unit")
    discontinued = fields.Boolean(string="Discontinued", default=False, index=True, help="If checked, this product has been discontinued by the manufacturer but remains in the system for backward compatibility.")

class ResPartner(models.Model):
    _inherit = "res.partner"

    pricelist_id = fields.Many2one("product.pricelist", "Pricelist_Sync")

    # product.res_partner already defines a compute of this same name for
    # property_product_pricelist (falls back to a country/company default
    # pricelist for every partner via _get_partner_pricelist_multi). Since
    # this method has the same name, it replaces rather than extends that
    # one — call super() first so partners with no synced pricelist_id keep
    # a valid fallback pricelist (needed e.g. for the website Shop page's
    # sale.order, which requires one), then only override for partners
    # ProSync has actually assigned one to.
    @api.depends("pricelist_id", "country_id", "specific_property_product_pricelist")
    @api.depends_context("company", "country_code")
    def _compute_product_pricelist(self):
        super()._compute_product_pricelist()
        for p in self.filtered("pricelist_id"):
            p.property_product_pricelist = p.pricelist_id