# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

# Customer-facing pricelists are named EXACTLY by these flag emojis.
CAD_PRICELIST_NAME = '🇨🇦'
USD_PRICELIST_NAME = '🇺🇸'


class ProwebsiteController(http.Controller):

    @http.route(
        '/omnigo/sync_pricelist',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def sync_pricelist(self, **kw):
        """Report the resolved pricelist and align the cart to it.

        The OmniGO page renders its price server-side (QWeb) and updates on a
        full reload, so the pricelist is resolved entirely by
        proproduct.get_current_pricelist (region cookie -> geo-IP fallback).
        This handler must NOT mutate the session; it only reports the resolved
        pricelist (so the JS can show the currency badge) and aligns any
        existing cart order before the following /shop/cart/update_json.
        """
        pricelist = request.website.get_current_pricelist()

        try:
            order = request.website.sale_get_order(force_create=False)
            if order and order.pricelist_id.id != pricelist.id:
                _logger.info(
                    "[omnigo] Updating cart %s pricelist %s → %s",
                    order.name, order.pricelist_id.display_name, pricelist.display_name,
                )
                order.sudo().write({'pricelist_id': pricelist.id})
                try:
                    order.sudo()._recompute_prices()
                except AttributeError:
                    order.sudo()._recompute_all_prices()
        except Exception as e:
            _logger.warning("[omnigo] Could not update cart pricelist: %s", e)

        pl_sudo = pricelist.sudo()
        return {
            'pricelist_id': pricelist.id,
            'pricelist_name': pl_sudo.display_name,
            'currency': pl_sudo.currency_id.name,
        }

    @http.route(
        '/omnigo/get_pricelists',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def get_pricelists(self, **kw):
        """Return the CA / US pricelists for the header currency switcher.

        Resolved by exact flag-emoji name (matching proproduct/models/website.py)
        and marked active against the visitor's current region (cookie or geo-IP).
        """
        website = request.website
        try:
            current_region = website.proproduct_region()  # 'US' / 'CA'
        except Exception:
            current_region = None

        Pricelist = request.env['product.pricelist'].sudo()
        website_domain = ['|', ('website_id', '=', False), ('website_id', '=', website.id)]

        result = []
        for region, name, currency in [
            ('CA', CAD_PRICELIST_NAME, 'CAD'),
            ('US', USD_PRICELIST_NAME, 'USD'),
        ]:
            pl = Pricelist.search([('name', '=', name)] + website_domain, limit=1)
            if not pl:
                continue
            result.append({
                'id':       pl.id,
                'label':    region,        # 'US' / 'CA' — the pl_region cookie value
                'flag':     name,          # the flag emoji itself
                'currency': currency,
                'active':   region == current_region,
            })
        return result
