# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    approve_financing = fields.Boolean("Approve Financing", default=False, help="If checked, the eCommerce page will show an APPROVE financing section.")
    show_add_to_cart = fields.Boolean("Show Add to Cart Button", default=False, help="If checked, the eCommerce page will show an Add To Cart button.")

    is_us = fields.Boolean(string='Is Published in US')
    is_ca = fields.Boolean(string='Is Published in CA')

    def action_is_us_toggle(self):
        self.is_us = not self.is_us

    def action_is_ca_toggle(self):
        self.is_ca = not self.is_ca

    # filter products on store based on country pubished status
    def _get_website_domain(self, website_id):
        domain = super()._get_website_domain(website_id)

        # Only filter when on /shop requests
        if not http.request:
            return domain
        path = http.request.httprequest.path
        if not path.startswith('/shop'):
            return domain

        # Determine current pricelist
        website = http.request.env['website'].browse(website_id)
        pricelist = website.get_current_pricelist()
        
        _logger.info(f"[proproduct] Filtering products for /shop, pricelist: {pricelist.name}, currency: {pricelist.currency_id.name}")

        # Apply is_us / is_ca filters
        if pricelist.currency_id.name == 'USD':
            _logger.info("[proproduct] Applying filter: ('is_us', '=', True)")
            domain.append(('is_us', '=', True))
        elif pricelist.currency_id.name == 'CAD':
            _logger.info("[proproduct] Applying filter: ('is_ca', '=', True)")
            domain.append(('is_ca', '=', True))
        else:
            _logger.info("[proproduct] No is_us/is_ca filter applied for this currency.")

        _logger.info(f"[proproduct] Final computed domain for shop: {domain}")

        return domain

