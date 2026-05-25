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
        Sync the website session to the geo-IP-correct pricelist and update any
        existing cart order to match.

        Why this is needed:
          - Our custom OmniGO page renders og_pl in QWeb for display only — it
            never sets request.session['website_sale_current_pl'].
          - proproduct's sale_get_pricelist() skips geo detection when
            'pricelist_selected_manually' is in the session (set e.g. by the
            shop's pricelist switcher), leaving a stale CAD pricelist in the cart.
          - Standard _get_current_pricelist() does not use proproduct's geo logic.

        Fix:
          1. Clear both stale session flags so sale_get_pricelist() runs its
             full geo-IP path (visitor_geoinfo → "USD Pricelist" / "CAD Pricelist").
          2. Write the result back into the session.
          3. Directly update the existing cart order's pricelist so the
             immediately-following /shop/cart/update_json call uses it.
        """
        # 1. Clear stale overrides — manual selection on the /shop page must not
        #    bleed into our dedicated product page.
        request.session.pop('pricelist_selected_manually', None)
        request.session.pop('website_sale_current_pl', None)

        # 2. Resolve the geo-correct pricelist.
        #    Prefer proproduct's sale_get_pricelist() which does visitor_geoinfo
        #    + "USD Pricelist" / "CAD Pricelist" name lookup.
        #    Fall back to Odoo's _get_current_pricelist() if that method is absent.
        pricelist = None
        if hasattr(request.website, 'sale_get_pricelist'):
            try:
                pricelist = request.website.sale_get_pricelist()
            except Exception as e:
                _logger.warning("[omnigo] sale_get_pricelist() failed: %s", e)

        if not pricelist and hasattr(request.website, '_get_current_pricelist'):
            pricelist = request.website._get_current_pricelist()

        if not pricelist:
            _logger.warning("[omnigo] Could not resolve pricelist — returning early")
            return {'pricelist_id': None}

        # sale_get_pricelist() already writes the session, but be explicit.
        request.session['website_sale_current_pl'] = pricelist.id

        # 3. Update the existing cart order immediately so cart_update_json
        #    does not re-create it with the old pricelist.
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
            'pricelist_name': pl_sudo.name,
            'currency': pl_sudo.currency_id.name,
        }
