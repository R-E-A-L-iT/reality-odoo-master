# -*- coding: utf-8 -*-
import logging
from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale

_logger = logging.getLogger(__name__)

class WebsiteSalePricelistFilter(WebsiteSale):

    _logger.info("[proproduct] Initializing WebsiteSalePricelistFilter")

    def _get_shop_domain(self, search, category, attrib_values):
        domain = super()._get_shop_domain(search, category, attrib_values)

        website = http.request.env['website'].get_current_website()
        pricelist = website.get_current_pricelist()

        _logger.info(f"[proproduct] Current pricelist: {pricelist.name} (currency: {pricelist.currency_id.name})")

        if pricelist.currency_id.name == 'USD':
            _logger.info("[proproduct] Adding filter: ('is_us', '=', True)")
            domain.append(('is_us', '=', True))
        elif pricelist.currency_id.name == 'CAD':
            _logger.info("[proproduct] Adding filter: ('is_ca', '=', True)")
            domain.append(('is_ca', '=', True))
        else:
            _logger.info("[proproduct] No filter applied for this pricelist.")

        _logger.info(f"[proproduct] Final shop domain: {domain}")

        return domain
