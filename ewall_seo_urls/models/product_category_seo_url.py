# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.addons.http_routing.models.ir_http import slug, unslug

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

    def _compute_website_url(self):
        res = super(ProductTemplate, self)._compute_website_url()
        for product in self:
            if product.seo_url:
                product.website_url = "/shop/%s" % (product.seo_url)
            elif product.id:
                product.website_url = "/shop/%s" % slug(product)
        return res


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

# Product Hover Product ID Remove Functionality 
class ProductProductInherit(models.Model):
    _inherit = "product.product"

    def _compute_product_website_url(self):
        res = super(ProductProductInherit, self)._compute_product_website_url()
        for product in self:
            attributes = ','.join(str(x) for x in product.product_template_attribute_value_ids.ids)
            if attributes:
                product.website_url = "%s#attr=%s" % (product.product_tmpl_id.website_url, attributes)
            else:
                product.website_url = product.product_tmpl_id.website_url
        return res