import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)


def _get_country_code():
    """
    Return the ISO country code for the current HTTP request.

    Uses request.geoip, which Odoo populates from X-Forwarded-For (the real
    client IP behind load-balancers / cloud proxies).  This is more reliable
    than visitor_geoinfo() which can fall back to REMOTE_ADDR — the cloud
    server's own IP — and therefore wrongly return 'CA' for every visitor.
    """
    try:
        geoip = request.geoip if hasattr(request, 'geoip') else {}
        return (geoip or {}).get('country_code') or None
    except Exception:
        return None


def _pricelist_for_currency(env, website, currency_name):
    """
    Return the first non-rental pricelist in *currency_name* available on *website*.

    Rental pricelists (e.g. "USD RENTAL") are intentionally excluded so that the
    regular customer-facing pricelist is always selected over any rental variant.
    """
    return env['product.pricelist'].sudo().search([
        ('currency_id.name', '=', currency_name),
        ('name', 'not ilike', 'rent'),
        '|', ('website_id', '=', False), ('website_id', '=', website.id),
    ], limit=1)


class Website(models.Model):
    _inherit = 'website'

    def sale_get_pricelist(self, partner=False):
        self.ensure_one()

        # Outside an HTTP request (cron, backend) — use website default safely.
        if not request:
            return self.pricelist_id

        # Let Odoo's parent implementation resolve any partner / session logic first.
        parent = super(Website, self)
        if hasattr(parent, 'sale_get_pricelist'):
            pricelist = parent.sale_get_pricelist(partner=partner)
        else:
            _logger.warning(
                "[proproduct] parent.sale_get_pricelist not found. "
                "Falling back to website.pricelist_id."
            )
            pricelist = self.pricelist_id

        # If the user explicitly chose a pricelist (e.g. via the /shop switcher),
        # honour that choice and skip geo-detection.
        if request.session.get('pricelist_selected_manually'):
            _logger.info("[proproduct] Pricelist manually selected — skipping geo override.")
            request.session['website_sale_current_pl'] = pricelist.id
            return pricelist

        # --- Geo-IP detection ---
        # request.geoip is populated from X-Forwarded-For by Odoo's WSGI middleware,
        # so it reflects the *real* user IP even behind cloud proxies.
        # visitor_geoinfo() was previously used here but it can resolve to the
        # server's own IP (which is Canadian for our cloud host), causing every
        # visitor to be treated as Canadian regardless of their actual location.
        country_code = _get_country_code()
        _logger.info("[proproduct] geo country_code=%s", country_code)

        env = request.env

        if country_code == 'US':
            usd_pl = _pricelist_for_currency(env, self, 'USD')
            if usd_pl:
                pricelist = usd_pl
                _logger.info("[proproduct] geo → USD pricelist: %s", usd_pl.display_name)
            else:
                _logger.warning("[proproduct] No USD pricelist found; keeping default.")
        else:
            # Canada + all other countries → CAD (per business rule).
            cad_pl = _pricelist_for_currency(env, self, 'CAD')
            if cad_pl:
                pricelist = cad_pl
                _logger.info("[proproduct] geo → CAD pricelist: %s", cad_pl.display_name)
            else:
                _logger.warning("[proproduct] No CAD pricelist found; keeping default.")

        request.session['website_sale_current_pl'] = pricelist.id
        return pricelist

    def sale_get_order(self, force_create=False, **kwargs):
        order = super().sale_get_order(force_create=force_create, **kwargs)

        if not order or not request:
            return order

        # Honour explicit user selection.
        if request.session.get('pricelist_selected_manually'):
            return order

        # Ensure the cart's pricelist matches the geo-detected one.
        desired_pl = self.sale_get_pricelist(partner=order.partner_id)
        if desired_pl and order.pricelist_id != desired_pl:
            _logger.info(
                "[proproduct] Updating cart %s pricelist %s → %s",
                order.name,
                order.pricelist_id.display_name,
                desired_pl.display_name,
            )
            order = order.sudo()
            order.write({'pricelist_id': desired_pl.id})
            order._recompute_prices()

        return order
