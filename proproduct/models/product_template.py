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

        # Only filter on /shop pages
        if not http.request:
            return domain
        path = http.request.httprequest.path
        if not path.startswith('/shop'):
            return domain

        # Retrieve the active pricelist_id from session explicitly
        pricelist_id = http.request.session.get('website_sale_current_pl')
        pricelist = None
        if pricelist_id:
            pricelist = http.request.env['product.pricelist'].sudo().browse(pricelist_id)

        if pricelist:
            _logger.info(f"[proproduct] Filtering products for /shop, pricelist: {pricelist.name}, currency: {pricelist.currency_id.name}")

            if pricelist.currency_id.name == 'USD':
                _logger.info("[proproduct] Applying filter: ('is_us', '=', True)")
                domain.append(('is_us', '=', True))
            elif pricelist.currency_id.name == 'CAD':
                _logger.info("[proproduct] Applying filter: ('is_ca', '=', True)")
                domain.append(('is_ca', '=', True))
            else:
                _logger.info("[proproduct] No is_us/is_ca filter applied for this currency.")
        else:
            _logger.info("[proproduct] No active pricelist found in session; skipping is_us/is_ca filtering.")

        _logger.info(f"[proproduct] Final computed domain for shop: {domain}")

        return domain
