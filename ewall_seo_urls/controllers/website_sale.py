# -*- coding: utf-8 -*-
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo import http
from odoo import fields, http, SUPERUSER_ID, tools, _

# Website Sale Cotroller
class WebsiteSaleCategory(WebsiteSale):

    # Shop Attributes SEO URL Name Added
    def _shop_get_query_url_kwargs(self, category, search, min_price, max_price, attrib=None, order=None, **post):
        category_id = request.env['product.public.category'].sudo().browse(category)
        category = category_id.seo_url if category_id.seo_url else category
        return super()._shop_get_query_url_kwargs(category, search, min_price, max_price, attrib, order, **post)

    # Product Page SEO URL Name Added
    def _prepare_product_values(self, product, category, search, **kwargs):
        if category:
            category_id = request.env['product.public.category'].sudo().search([('seo_url','=',category)],limit=1)
            category = category_id.id if category_id else category
        return super()._prepare_product_values(product, category, search, **kwargs)

    # Shop Page SEO URL Name Added
    @http.route()
    def shop(self, page=0, category=None, search='', min_price=0.0, max_price=0.0, ppg=False, **post):
        if category:
            if isinstance(category, str):
                category = request.env['product.public.category'].sudo().search([('seo_url', '=', category)], limit=1)
        return super().shop(page, category, search, min_price, max_price, ppg, **post)
