# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


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
        Ensure the website session carries the geo-IP-correct pricelist so that
        subsequent /shop/cart/update_json calls use the right pricing.

        The problem this solves: our custom OmniGO product page computes the
        correct pricelist in QWeb (via og_pl) for display purposes, but never
        writes it to request.session['website_sale_current_pl']. If the user
        previously visited the site with a different country/pricelist, the
        stale session value overrides geo-IP detection when Odoo resolves the
        cart's pricelist inside sale_get_order().

        Fix: clear the stale override and let Odoo's _get_current_pricelist()
        recalculate from geo-IP + website defaults. The result is stored back
        in the session so the immediately-following cart_update_json call
        picks it up.
        """
        # Drop any stale override so geo-IP detection takes over.
        request.session.pop('website_sale_current_pl', None)

        if not hasattr(request.website, '_get_current_pricelist'):
            # website_sale not installed — nothing to do.
            return {'pricelist_id': None}

        pricelist = request.website._get_current_pricelist()
        request.session['website_sale_current_pl'] = pricelist.id

        return {
            'pricelist_id': pricelist.id,
            'pricelist_name': pricelist.sudo().name,
            'currency': pricelist.sudo().currency_id.name,
        }
