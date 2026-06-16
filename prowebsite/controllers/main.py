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
        Sync the website session to the correct pricelist and immediately
        update any existing cart order to match.

        Why this is needed:
          Our custom OmniGO product page renders og_pl (and the displayed price)
          via QWeb but never writes og_pl.id to the session. A stale session
          pricelist would cause /shop/cart/update_json to use the wrong price.

        Pricelist precedence is delegated entirely to
        proproduct.get_current_pricelist (region cookie -> geo-IP fallback).
        This handler must NOT mutate the session — it only reports the resolved
        pricelist and aligns the existing cart order to it.
        """
        pricelist = request.website.get_current_pricelist()

        # Align an existing cart order now so the immediately-following
        # /shop/cart/update_json sees the right pricelist.
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
        """Return CA / US pricelists for the header currency switcher.

        Mirrors the logic in proproduct/models/website.py:
        - identified by currency (CAD / USD), not by name
        - rental pricelists excluded (name ilike 'rent')
        - scoped to current website or global
        """
        website = request.website

        current_pl = None
        try:
            current_pl = website.sale_get_pricelist()
        except Exception:
            pass

        Pricelist = request.env['product.pricelist'].sudo()
        website_domain = ['|', ('website_id', '=', False), ('website_id', '=', website.id)]

        result = []
        for currency_name, label, flag in [('CAD', 'CA', '🇨🇦'), ('USD', 'US', '🇺🇸')]:
            pl = Pricelist.search(
                [('currency_id.name', '=', currency_name),
                 ('name', 'not ilike', 'rent')] + website_domain,
                limit=1,
            )
            if not pl:
                continue
            result.append({
                'id':       pl.id,
                'label':    label,
                'flag':     flag,
                'currency': currency_name,
                'active':   bool(current_pl and pl.id == current_pl.id),
            })
        return result

    @http.route(
        '/omnigo/set_pricelist',
        type='json',
        auth='public',
        website=True,
        csrf=False,
    )
    def set_pricelist(self, pricelist_id=None, **kw):
        """Manually pin a session pricelist and update the active cart."""
        if not pricelist_id:
            return {'success': False}

        pl = request.env['product.pricelist'].sudo().browse(int(pricelist_id))
        if not pl.exists():
            return {'success': False}

        request.session['website_sale_current_pl'] = pl.id
        request.session['pricelist_selected_manually'] = True

        try:
            order = request.website.sale_get_order(force_create=False)
            if order and order.pricelist_id.id != pl.id:
                order.sudo().write({'pricelist_id': pl.id})
                try:
                    order.sudo()._recompute_prices()
                except AttributeError:
                    order.sudo()._recompute_all_prices()
        except Exception as e:
            _logger.warning("[omnigo] set_pricelist cart update failed: %s", e)

        return {
            'success':  True,
            'currency': pl.currency_id.name,
        }
