import logging

from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

try:
    # v19 caches the resolved pricelist per session under this key.
    from odoo.addons.website_sale.models.website import PRICELIST_SESSION_CACHE_KEY
except ImportError:  # pragma: no cover - defensive if the constant ever moves
    PRICELIST_SESSION_CACHE_KEY = 'website_sale_current_pl'

# Business rule: the customer-facing pricelists are named EXACTLY by these flag
# emojis. Resolved by name (not by currency) so the right one is chosen even when
# several share a currency (e.g. a separate rental pricelist in CAD).
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
    """ISO country code for the current request, from Odoo's geoip resolution."""
    try:
        geoip = request.geoip if hasattr(request, 'geoip') else {}
        return (geoip or {}).get('country_code') or None
    except Exception:
        return None


def _selected_region():
    """Region the visitor explicitly picked via the header switcher, or None."""
    try:
        region = request.httprequest.cookies.get(REGION_COOKIE)
    except Exception:
        return None
    return region if region in _REGION_PRICELIST_NAME else None


def _pricelist_by_name(env, website, name):
    """Pricelist named exactly *name*, global or scoped to *website*.

    Tolerates duplicates: prefers one scoped to this website, then one that
    actually has price rules (avoids an empty leftover), then the lowest id.
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
    # Pricelist resolution (Odoo 19)
    # ------------------------------------------------------------------
    # Precedence:
    #   1. the region the visitor explicitly picked (cookie `pl_region`), which
    #      always wins and persists across navigation;
    #   2. otherwise the geo-IP country: US -> USD, everywhere else -> CAD.
    #
    # Odoo 19 REPLACED the frontend pricelist API this module used to hook.
    # `get_current_pricelist`, `_get_current_pricelist`, `sale_get_pricelist` and
    # `sale_get_order` no longer exist on `website`; resolution now runs through
    # `_get_and_cache_current_pricelist()` (exposed as `request.pricelist`) and the
    # cart through `request.cart`. The old overrides were dead code — they defined
    # methods nothing called, so every visitor silently got core's pricelist.

    def proproduct_region(self):
        """Active region code ('US' or 'CA') for this request."""
        region = _selected_region()
        if region:
            return region
        return 'US' if _get_country_code() == 'US' else 'CA'

    def _proproduct_resolve_pricelist(self):
        """Pricelist for the current visitor, or an empty recordset to defer."""
        if not request:
            return self.env['product.pricelist']
        region = self.proproduct_region()
        name = _REGION_PRICELIST_NAME[region]
        pl = _pricelist_by_name(request.env, self, name)
        if not pl:
            _logger.warning(
                "[proproduct] no pricelist named %r for region %s — deferring to core.",
                name, region,
            )
        return pl

    def _get_and_cache_current_pricelist(self):
        """Resolve the storefront pricelist from the region, not the session.

        Core caches its answer in the session and only recomputes when the cached
        pricelist becomes unavailable — so a visitor switching region would keep
        the old currency until the session expired. We resolve first and then
        overwrite the cache, keeping anything that reads the session key in sync.
        """
        self.ensure_one()
        pl = self._proproduct_resolve_pricelist()
        if not pl:
            return super()._get_and_cache_current_pricelist()

        pl_sudo = pl.sudo()
        try:
            request.session[PRICELIST_SESSION_CACHE_KEY] = pl_sudo.id
        except Exception:
            pass

        # Keep the active cart on the same pricelist; core normally does this
        # inside the method we just short-circuited.
        try:
            cart_sudo = request.cart
            if cart_sudo and not request.env.cr.readonly \
                    and cart_sudo.pricelist_id != pl_sudo:
                _logger.info(
                    "[proproduct] cart %s pricelist %s -> %s",
                    cart_sudo.name, cart_sudo.pricelist_id.display_name,
                    pl_sudo.display_name,
                )
                cart_sudo.write({'pricelist_id': pl_sudo.id})
                cart_sudo._recompute_prices()
        except Exception as e:
            _logger.warning("[proproduct] cart pricelist sync failed: %s", e)

        return pl_sudo

    # ------------------------------------------------------------------
    # Compatibility shims
    # ------------------------------------------------------------------
    # Odoo 19 dropped these names, but proproduct's own QWeb/models (and the
    # OmniGO page) still call them. They must NOT call super() — there is no
    # parent implementation any more.

    def get_current_pricelist(self):
        self.ensure_one()
        return self._get_and_cache_current_pricelist()

    def sale_get_pricelist(self, partner=False):
        self.ensure_one()
        return self._get_and_cache_current_pricelist()
