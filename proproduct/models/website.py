import logging
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

# Business rule: the customer-facing pricelists are named EXACTLY by these flag
# emojis.  We resolve by name (not by currency) so the right pricelist is chosen
# even if several share a currency (e.g. a separate rental pricelist in CAD).
CAD_PRICELIST_NAME = '🇨🇦'
USD_PRICELIST_NAME = '🇺🇸'

# Cookie written by the header currency switcher
# (prowebsite/static/src/js/header_dropdowns.js). Value: 'US' or 'CA'.
REGION_COOKIE = 'pl_region'

_REGION_PRICELIST_NAME = {
    'US': USD_PRICELIST_NAME,
    'CA': CAD_PRICELIST_NAME,
}


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


def _selected_region():
    """Region the visitor explicitly picked via the header switcher, or None.

    Read from the `pl_region` cookie, which the switcher sets *before* it
    reloads, so it always rides along on the request.
    """
    try:
        region = request.httprequest.cookies.get(REGION_COOKIE)
    except Exception:
        return None
    return region if region in _REGION_PRICELIST_NAME else None


def _pricelist_by_name(env, website, name):
    """Pricelist named exactly *name*, global or scoped to *website*.

    Robust against duplicate same-named pricelists (clutter): when several share
    the name, prefer one scoped to this website, then one that actually has price
    rules (avoids picking an empty leftover duplicate), then the lowest id.
    """
    pricelists = env['product.pricelist'].sudo().search([
        ('name', '=', name),
        '|', ('website_id', '=', False), ('website_id', '=', website.id),
    ])
    if len(pricelists) <= 1:
        return pricelists
    _logger.warning(
        "[proproduct] %d pricelists named %r found (ids=%s) — using best match; "
        "consider de-duplicating.", len(pricelists), name, pricelists.ids,
    )
    return pricelists.sorted(
        key=lambda p: (p.website_id.id != website.id, not p.item_ids, p.id)
    )[:1]


class Website(models.Model):
    _inherit = 'website'

    # ------------------------------------------------------------------
    # Pricelist resolution  (Odoo 17)
    # ------------------------------------------------------------------
    # The customer-facing price (product page, /shop, cart, and the OmniGO
    # page's server-rendered price) is resolved through the methods below.
    # Precedence:
    #   1. The region the visitor explicitly picked (cookie `pl_region`) — this
    #      ALWAYS wins and persists across navigation (requirement 1).
    #   2. Otherwise the geo-IP detected country — the regional default
    #      (requirement 2): US -> USD, everywhere else -> CAD.
    # The pricelist is resolved by its exact flag-emoji name and returned
    # directly, so core's availability filter can never strip it.

    def proproduct_region(self):
        """Return the active region code ('US' or 'CA') for this request."""
        region = _selected_region()
        if region:
            _logger.info("[proproduct] region cookie=%s", region)
            return region
        country = _get_country_code()
        region = 'US' if country == 'US' else 'CA'
        _logger.info("[proproduct] geo country=%s -> region=%s", country, region)
        return region

    def _proproduct_resolve_pricelist(self):
        """Pricelist for the current visitor, or empty recordset to defer."""
        if not request:
            return self.env['product.pricelist']
        region = self.proproduct_region()
        name = _REGION_PRICELIST_NAME[region]
        pl = _pricelist_by_name(request.env, self, name)
        raw_cookie = None
        try:
            raw_cookie = request.httprequest.cookies.get(REGION_COOKIE)
        except Exception:
            pass
        _logger.info(
            "[proproduct] resolve | raw pl_region cookie=%r | region=%s | "
            "looking for pricelist named %r | found=%s",
            raw_cookie, region, name, (pl.display_name if pl else None),
        )
        if not pl:
            _logger.warning("[proproduct] No pricelist named %r found.", name)
        return pl

    def get_current_pricelist(self):
        """Override the Odoo 17 frontend pricelist resolver."""
        self.ensure_one()
        pl = self._proproduct_resolve_pricelist()
        if pl:
            _logger.info("[proproduct] get_current_pricelist -> %s (%s)",
                         pl.display_name, pl.currency_id.name)
            return pl
        _logger.info("[proproduct] get_current_pricelist -> deferring to core (no match)")
        return super().get_current_pricelist()

    def _get_current_pricelist(self):
        """Defensive override of the internal resolver some Odoo 17 builds use."""
        self.ensure_one()
        pl = self._proproduct_resolve_pricelist()
        if pl:
            return pl
        parent = super()
        if hasattr(parent, '_get_current_pricelist'):
            return parent._get_current_pricelist()
        return self.get_current_pricelist()

    def sale_get_pricelist(self, partner=False):
        """Compat name used by the OmniGO page QWeb and other custom code.

        Odoo <=16 used `sale_get_pricelist`; Odoo 17 core dropped it. We keep it
        and route it through the same resolver so every code path agrees.
        """
        self.ensure_one()
        pl = self._proproduct_resolve_pricelist()
        if pl:
            return pl
        parent = super()
        if hasattr(parent, 'sale_get_pricelist'):
            return parent.sale_get_pricelist(partner=partner)
        return self.pricelist_id

    def sale_get_order(self, force_create=False, **kwargs):
        """Keep the active cart aligned with the resolved pricelist."""
        order = super().sale_get_order(force_create=force_create, **kwargs)
        if not order or not request:
            return order
        desired_pl = self.get_current_pricelist()
        if desired_pl and order.pricelist_id != desired_pl:
            _logger.info(
                "[proproduct] Updating cart %s pricelist %s -> %s",
                order.name, order.pricelist_id.display_name, desired_pl.display_name,
            )
            order = order.sudo()
            order.write({'pricelist_id': desired_pl.id})
            order._recompute_prices()
        return order
