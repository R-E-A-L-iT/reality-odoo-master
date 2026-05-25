# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request

import logging
_logger = logging.getLogger(__name__)


class ProwebsiteController(http.Controller):

    @http.route(
        '/omnigo/sync_pricelist',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def sync_pricelist(self, **kw):
        """
        Sync the website session to the geo-IP-correct pricelist and immediately
        update any existing cart order to match.

        Why this is needed:
          Our custom OmniGO product page renders og_pl (and the displayed price)
          via QWeb but never writes og_pl.id to the session. A stale session
          pricelist (e.g. from a previous visit or from the /shop pricelist
          switcher) would cause /shop/cart/update_json to use the wrong price.

        What we do:
          1. Clear pricelist_selected_manually — the switcher on /shop must not
             bleed into our dedicated product page.
          2. Clear website_sale_current_pl — remove any stale session value.
          3. Call sale_get_pricelist() — proproduct's geo-aware method, now fixed
             to use request.geoip (real user IP) and search by currency instead
             of by pricelist name.
          4. Directly update the existing cart order's pricelist so that the
             immediately-following /shop/cart/update_json call sees the right one.
        """
        request.session.pop('pricelist_selected_manually', None)
        request.session.pop('website_sale_current_pl', None)

        if not hasattr(request.website, 'sale_get_pricelist'):
            _logger.warning("[omnigo] sale_get_pricelist() not available")
            return {'pricelist_id': None}

        try:
            pricelist = request.website.sale_get_pricelist()
        except Exception as e:
            _logger.error("[omnigo] sale_get_pricelist() raised: %s", e)
            return {'pricelist_id': None}

        # sale_get_pricelist() already writes the session, but be explicit.
        request.session['website_sale_current_pl'] = pricelist.id

        # Update an existing cart order right now so there is no window between
        # this call and the subsequent cart_update_json where the old pricelist
        # could be used.
        try:
            order = request.website.sale_get_order(force_create=False)
            if order and order.pricelist_id.id != pricelist.id:
                _logger.info(
                    "[omnigo] Updating cart %s pricelist %s → %s",
                    order.name,
                    order.pricelist_id.display_name,
                    pricelist.display_name,
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
