# -*- coding: utf-8 -*-
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteSalePricelistFilter(WebsiteSale):

    def _get_shop_domain(self, search, category, attrib_values):
        domain = super()._get_shop_domain(search, category, attrib_values)

        website = http.request.env['website'].get_current_website()
        pricelist = website.get_current_pricelist()

        if pricelist.currency_id.name == 'USD':
            domain.append(('is_us', '=', True))
        elif pricelist.currency_id.name == 'CAD':
            domain.append(('is_ca', '=', True))

        return domain
