# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

class WebsiteSaleInherit(WebsiteSale):

    def _get_search_domain(self, search, category, attrib_values, **kwargs):
        
        # get default domain
        domain = super(WebsiteSaleInherit, self)._get_search_domain(search, category, attrib_values, **kwargs)
        
        # get current pricelist
        pricelist = request.website.get_current_pricelist()
        if pricelist.currency_id: 
            currency = pricelist.currency_id

            # append filters
            if currency.name == 'USD':
                domain += [('is_us', '=', True)]
            elif currency.name == 'CAD':
                domain += [('is_ca', '=', True)]
                
        return domain
