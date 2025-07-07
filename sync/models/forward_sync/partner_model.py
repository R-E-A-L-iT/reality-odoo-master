from odoo import fields, models, api


class Partner(models.Model):
    _inherit = "res.partner"
    pricelist_id = fields.Many2one("product.pricelist", "Pricelist_Sync")

    @api.depends("pricelist_id")
    # Connect the calulate field that odoo uses to a stored field that can be set by internal users
    def _compute_product_pricelist(self):
        for p in self:
            p.property_product_pricelist = p.pricelist_id
