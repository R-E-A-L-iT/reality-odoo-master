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


# Cookie written client-side by the header flag/language switcher
# (prowebsite/static/src/js/header_dropdowns.js) when the visitor explicitly
# picks a region.  Value is an ISO-3166 alpha-2 country code, e.g. 'US' / 'CA'.
REGION_COOKIE = 'pl_region'

# Region -> currency mapping for the customer-facing pricelist.
_REGION_CURRENCY = {
    'US': 'USD',
    'CA': 'CAD',
}
_DEFAULT_CURRENCY = 'CAD'  # business rule: everyone outside the US gets CAD


def _currency_for_country(country_code):
    """Map an ISO country code to the store currency (defaults to CAD)."""
    if country_code == 'US':
        return 'USD'
    return _DEFAULT_CURRENCY


def _selected_region():
    """Return the region the visitor explicitly chose via the flag switcher.

    Read from the `pl_region` cookie, which the header dropdown sets *before*
    the language navigation fires, so it always rides along on the request.
    Returns None when the visitor has not made an explicit choice yet.
    """
    try:
        region = request.httprequest.cookies.get(REGION_COOKIE)
    except Exception:
        return None
    return region if region in _REGION_CURRENCY else None


class Website(models.Model):
    _inherit = 'website'

    # ------------------------------------------------------------------
    # Pricelist resolution  (Odoo 17)
    # ------------------------------------------------------------------
    # The customer-facing price (product page, /shop, cart) is resolved through
    # `get_current_pricelist()`.  We override it to drive the pricelist from:
    #
    #   1. The region the visitor explicitly picked with the header flag/language
    #      switcher (cookie `pl_region`) — this ALWAYS wins (requirement 1).
    #   2. Otherwise the geo-IP detected country — the regional default
    #      (requirement 2): US -> USD, everywhere else -> CAD.
    #
    # We return the resolved pricelist *directly* so core's availability filter
    # (`get_pricelist_available`) can never strip a country-restricted pricelist.

    def _proproduct_target_currency(self):
        """Return the currency code the current visitor should see."""
        region = _selected_region()
        if region:
            currency = _REGION_CURRENCY[region]
            _logger.info("[proproduct] region cookie=%s -> %s", region, currency)
            return currency
        country = _get_country_code()
        currency = _currency_for_country(country)
        _logger.info("[proproduct] geo country=%s -> %s", country, currency)
        return currency

    def _proproduct_resolve_pricelist(self):
        """Return the pricelist to use, or an empty recordset to defer to core."""
        if not request:
            return self.env['product.pricelist']
        currency = self._proproduct_target_currency()
        pl = _pricelist_for_currency(request.env, self, currency)
        if pl:
            return pl
        _logger.warning("[proproduct] No %s pricelist found; deferring to core.", currency)
        return self.env['product.pricelist']

    def get_current_pricelist(self):
        """Override the Odoo 17 frontend pricelist resolver."""
        self.ensure_one()
        target = self._proproduct_resolve_pricelist()
        if target:
            _logger.info(
                "[proproduct] get_current_pricelist -> %s (%s)",
                target.display_name, target.currency_id.name,
            )
            return target
        return super().get_current_pricelist()

    def _get_current_pricelist(self):
        """Defensive override of the internal resolver some Odoo 17 builds use."""
        self.ensure_one()
        target = self._proproduct_resolve_pricelist()
        if target:
            return target
        parent = super()
        if hasattr(parent, '_get_current_pricelist'):
            return parent._get_current_pricelist()
        return self.get_current_pricelist()

    def sale_get_pricelist(self, partner=False):
        """Backward-compat alias for custom controllers/templates that call it
        (the Odoo <=16 name); routes through the canonical resolver."""
        self.ensure_one()
        return self.get_current_pricelist()

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
