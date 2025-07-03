# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.main import WebsiteSale

import logging
_logger = logging.getLogger(__name__)

class WebsiteSaleCurrencyFilter(WebsiteSale):

    def _get_shop_domain(self, search, category, attrib_values, search_in_description=True):
        # Get the default domain from Odoo
        domain = super()._get_shop_domain(search, category, attrib_values, search_in_description=search_in_description)
        
        website = request.env['website'].get_current_website()
        pricelist = website.get_current_pricelist()
        
        if pricelist and pricelist.currency_id:
            currency = pricelist.currency_id.name
            _logger.info(f"[proproduct] Active pricelist currency: {currency}")
            if currency == 'USD':
                _logger.info("[proproduct] Adding domain filter: ('is_us', '=', True)")
                domain.append(('is_us', '=', True))
            elif currency == 'CAD':
                _logger.info("[proproduct] Adding domain filter: ('is_ca', '=', True)")
                domain.append(('is_ca', '=', True))
            else:
                _logger.info("[proproduct] No currency-based filtering applied.")

        _logger.info(f"[proproduct] Final computed shop domain: {domain}")
        return domain