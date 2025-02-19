from odoo import models, fields, api

class PreconfiguredSection(models.Model):
    _name = 'preconfigured.section'
    _description = 'Preconfigured Sections'

    section_name = fields.Char(string='Section Name', required=True)
    section_description = fields.Text(string='Section Description')
    product_ids = fields.Many2many('product.product', string='Products')
    number_of_products = fields.Integer(string='Number of Products', compute='_compute_number_of_products')

    @api.depends('product_ids')
    def _compute_number_of_products(self):
        for record in self:
            record.number_of_products = len(record.product_ids)

class PreconfigSaleOrder(models.Model):
    _inherit = 'sale.order'

    preconfigured_section_ids = fields.Many2many('preconfigured.section', string='Preconfigured Sections')

class PreconfigSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    preconfigured_section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')