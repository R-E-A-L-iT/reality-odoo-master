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

    @api.onchange('product_id')
    def _onchange_product_name(self):
        if self.product_id:
            self.product_name = self.product_id.name
        else:
            self.product_name = False


class PreconfigSaleOrder(models.Model):
    _inherit = 'sale.order'

    preconfigured_section_ids = fields.Many2many('preconfigured.section', string='Preconfigured Sections')

    @api.onchange('preconfigured_section_ids')
    def _onchange_preconfigured_sections(self):
        if self.preconfigured_section_ids:
            new_lines = []
            for section in self.preconfigured_section_ids:
                new_lines.append((0, 0, {
                    'order_id': self.id,
                    'name': section.section_name,
                    'display_type': 'line_section',
                }))
                for line in section.product_line_ids:
                    new_lines.append((0, 0, {
                        'order_id': self.id,
                        'product_id': line.product_id.id,
                        'name': line.product_name,
                        'is_optional': line.optional,
                        'is_selected': line.selected,
                        'is_quantityLocked': line.quantity_locked,
                        'price_unit': line.price_unit,
                        'product_uom_qty': 1,
                    }))
            if new_lines:
                self.order_line = [(5, 0, 0)] + new_lines



class PreconfigSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    preconfigured_section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')