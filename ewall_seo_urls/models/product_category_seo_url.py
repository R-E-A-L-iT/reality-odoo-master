# -*- coding: utf-8 -*-
from odoo import fields, models

# Product Template Added SEO URL Field
class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "website_seo_url"]

    seo_url_language = fields.Selection(
        [('english', 'English'), ('arabic', 'Arabic')],
        string='URL Language',
        default='english',
        required=True,
        help='Select the language for the URL validation.',
    )

    seo_url = fields.Char("Product URL", help='URL field that supports only the selected language (English or Arabic).', index=True)


# Category Added SEO URL Field
class ProductPublicCategory(models.Model):
    _name = "product.public.category"
    _inherit = ["product.public.category", "website_seo_url"]

    seo_url_language = fields.Selection(
        [('english', 'English'), ('arabic', 'Arabic')],
        string='URL Language',
        default='english',
        required=True,
        help='Select the language for the URL validation.',
    )

    seo_url = fields.Char("Category URL", help='URL field that supports only the selected language (English or Arabic).', index=True)
