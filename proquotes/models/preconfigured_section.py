from odoo import models, fields, api

class PreconfiguredSection(models.Model):
    _name = 'preconfigured.section'
    _description = 'Preconfigured Sections'
    _rec_name = 'section_name'

    section_name = fields.Char(string='Section Name', required=True)
    section_description = fields.Text(string='Section Description')
    product_line_ids = fields.One2many('preconfigured.section.line', 'section_id')
    number_of_products = fields.Integer(string='Number of Products', compute='_compute_number_of_products')

    @api.depends('product_line_ids')
    def _compute_number_of_products(self):
        for record in self:
            record.number_of_products = 0
            record.number_of_products = len(record.product_line_ids)


class PreconfiguredSectionLine(models.Model):
    _name = 'preconfigured.section.line'
    _description = 'Preconfigured Section Line'
    _rec_name = 'product_name'

    section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    product_name = fields.Char(string='Name')
    optional = fields.Boolean(string='Optional')
    selected = fields.Boolean(string='Selected', default=True)
    quantity_locked = fields.Boolean(string='Quantity Locked')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Disc. (%)', default=0.0)

    @api.onchange('product_id')
    def _onchange_product_name(self):
        if self.product_id:
            self.product_name = self.product_id.name
            self.price_unit = self.product_id.lst_price
        else:
            self.product_name = False
            self.price_unit = 0.0
