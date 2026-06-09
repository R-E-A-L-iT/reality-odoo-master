# -*- coding: utf-8 -*-
from odoo import fields, models


class WebsiteQuotation(models.Model):
    _name = 'proquotes.website.quotation'
    _description = 'Website Quotation Request'

    company_name           = fields.Char(string='Company Name')
    partner_name           = fields.Char(string='Contact Name')
    quote_email            = fields.Char(string='Email')
    date_order             = fields.Datetime(string='Order Date')
    user_id                = fields.Many2one('res.users', string='Salesperson',
                                             domain=[('share', '=', False)])
    sale_order_template_id = fields.Many2one('sale.order.template', string='Quotation Template')
    pricelist_id           = fields.Many2one('product.pricelist', string='Pricelist',
                                             domain="[('name', 'not ilike', 'Default')]")
