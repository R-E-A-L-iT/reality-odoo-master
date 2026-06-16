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

        Precedence is delegated entirely to proproduct.get_current_pricelist:
          1. If the user explicitly chose a pricelist (any switcher writes
             'website_sale_current_pl'), that choice is honoured.
          2. Otherwise the geo-IP regional default is used.

        This handler must NOT touch the session itself: clearing or force-writing
        'website_sale_current_pl' here is exactly what wiped a manual USD
        selection on every page load. We only resolve the pricelist and align
        the existing cart order to it.
        """
        # ==============================================================
        # TEMPORARILY DISABLED — to observe Odoo's DEFAULT pricelist
        # behaviour, this handler is now a no-op.  It no longer resolves,
        # aligns the cart, or touches the session; core handles everything.
        # To restore: un-comment the block below.
        # ==============================================================
        pl = request.website.get_current_pricelist()
        return {
            'pricelist_id': pl.id,
            'pricelist_name': pl.sudo().display_name,
            'currency': pl.sudo().currency_id.name,
        }

        # if not hasattr(request.website, 'sale_get_pricelist'):
        #     _logger.warning("[omnigo] sale_get_pricelist() not available")
        #     return {'pricelist_id': None}
        #
        # try:
        #     pricelist = request.website.sale_get_pricelist()
        # except Exception as e:
        #     _logger.error("[omnigo] sale_get_pricelist() raised: %s", e)
        #     return {'pricelist_id': None}
        #
        # # Update an existing cart order right now so there is no window between
        # # this call and the subsequent cart_update_json where the old pricelist
        # # could be used.
        # try:
        #     order = request.website.sale_get_order(force_create=False)
        #     if order and order.pricelist_id.id != pricelist.id:
        #         _logger.info(
        #             "[omnigo] Updating cart %s pricelist %s → %s",
        #             order.name,
        #             order.pricelist_id.display_name,
        #             pricelist.display_name,
        #         )
        #         order.sudo().write({'pricelist_id': pricelist.id})
        #         try:
        #             order.sudo()._recompute_prices()
        #         except AttributeError:
        #             order.sudo()._recompute_all_prices()
        # except Exception as e:
        #     _logger.warning("[omnigo] Could not update cart pricelist: %s", e)
        #
        # pl_sudo = pricelist.sudo()
        # return {
        #     'pricelist_id': pricelist.id,
        #     'pricelist_name': pl_sudo.display_name,
        #     'currency': pl_sudo.currency_id.name,
        # }

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
