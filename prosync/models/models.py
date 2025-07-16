from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = "product.template"

    sku = fields.Char(string="SKU", readonly=False, index=True, help="Stock Keeping Unit")

class ResPartner(models.Model):
    _inherit = "res.partner"

    pricelist_id = fields.Many2one("product.pricelist", "Pricelist_Sync")

    @api.depends("pricelist_id")
    def _compute_product_pricelist(self):
        for p in self:
            p.property_product_pricelist = p.pricelist_id

class ProsyncReport(models.Model):
    _name = 'prosync.report'
    _description = 'ProSync Sync Report'

    name = fields.Char(string='Name', required=True)
    sync_type = fields.Selection([
        ('product_template', 'Product Template'),
        ('stock_lot', 'Stock/Lot'),
        ('res_partner', 'Contact'),
    ], string='Type', required=True)
    start_time = fields.Datetime(string='Start Time')
    end_time = fields.Datetime(string='End Time')