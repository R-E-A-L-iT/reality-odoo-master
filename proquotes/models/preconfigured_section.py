# -*- coding: utf-8 -*-

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
