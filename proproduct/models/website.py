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

    # ------------------------------------------------------------------
    # Pricelist resolution
    # ------------------------------------------------------------------
    # NOTE (Odoo 17): the customer-facing price (product page, shop, cart) is
    # resolved through `get_current_pricelist()`.  The old `sale_get_pricelist()`
    # method from Odoo <=16 no longer exists in core, so overriding it had no
    # effect on the displayed price — which is why a manually selected USD
    # pricelist was still rendering CAD prices.  We override the correct method
    # below and return the chosen pricelist *directly*, bypassing core's
    # `get_pricelist_available()` filter (which would otherwise discard a
    # country-restricted pricelist even when the user picked it explicitly).

    def _proproduct_resolve_pricelist(self):
        """
        Return the pricelist that should drive frontend prices, or an empty
        recordset to defer to core.

        Precedence (per business rule):
          1. The pricelist the user explicitly chose.  EVERY switcher route
             (Odoo core /shop/change_pricelist as well as our /omnigo and /shop
             set_pricelist routes) writes the chosen id to the session key
             'website_sale_current_pl'.  We deliberately never persist a geo
             default into that key, so its mere presence means "the user picked
             this" — and an explicit pick must always win (requirement 1).
          2. The geo-IP region default (US -> USD, everything else -> CAD).
             This is NOT written back to the session, so it stays dynamic until
             the user actually chooses something (requirement 2).
        """
        if not request:
            return self.env['product.pricelist']

        Pricelist = request.env['product.pricelist'].sudo()

        # 1. Explicit user choice (any switcher) always wins.
        pl_id = request.session.get('website_sale_current_pl')
        if pl_id:
            pl = Pricelist.browse(pl_id).exists()
            if pl:
                _logger.info("[proproduct] Honouring selected pricelist: %s", pl.display_name)
                return pl

        # 2. Geo-IP region default (not persisted).
        country_code = _get_country_code()
        currency = 'USD' if country_code == 'US' else 'CAD'
        _logger.info("[proproduct] geo country_code=%s -> %s", country_code, currency)
        pl = _pricelist_for_currency(request.env, self, currency)
        if pl:
            _logger.info("[proproduct] geo -> %s pricelist: %s", currency, pl.display_name)
            return pl

        _logger.warning("[proproduct] No %s pricelist found; deferring to core.", currency)
        return self.env['product.pricelist']

    # ==================================================================
    # TEMPORARILY DISABLED — custom pricelist resolution
    # ------------------------------------------------------------------
    # All custom geo / manual pricelist logic is commented out below so we can
    # observe Odoo's DEFAULT pricelist behaviour.  Only `sale_get_pricelist`
    # is kept as a thin alias to core's `get_current_pricelist`, because other
    # custom controllers/templates in this code base still call it and would
    # otherwise raise (core Odoo 17 has no `sale_get_pricelist`).
    #
    # To restore: un-comment the methods below and delete this alias.
    # ==================================================================

    def sale_get_pricelist(self, partner=False):
        """Compat alias only — defers entirely to core get_current_pricelist."""
        self.ensure_one()
        return self.get_current_pricelist()

    # def get_current_pricelist(self):
    #     """Override the Odoo 17 frontend pricelist resolver."""
    #     self.ensure_one()
    #     target = self._proproduct_resolve_pricelist()
    #     if target:
    #         _logger.info(
    #             "[proproduct] get_current_pricelist -> %s (%s)",
    #             target.display_name, target.currency_id.name,
    #         )
    #         return target
    #     return super().get_current_pricelist()

    # def _get_current_pricelist(self):
    #     """Defensive override of the internal Odoo 17 resolver."""
    #     self.ensure_one()
    #     target = self._proproduct_resolve_pricelist()
    #     if target:
    #         _logger.info(
    #             "[proproduct] _get_current_pricelist -> %s (%s)",
    #             target.display_name, target.currency_id.name,
    #         )
    #         return target
    #     parent = super()
    #     if hasattr(parent, '_get_current_pricelist'):
    #         return parent._get_current_pricelist()
    #     return self.get_current_pricelist()

    # def sale_get_order(self, force_create=False, **kwargs):
    #     order = super().sale_get_order(force_create=force_create, **kwargs)
    #     if not order or not request:
    #         return order
    #     desired_pl = self.get_current_pricelist()
    #     if desired_pl and order.pricelist_id != desired_pl:
    #         _logger.info(
    #             "[proproduct] Updating cart %s pricelist %s -> %s",
    #             order.name,
    #             order.pricelist_id.display_name,
    #             desired_pl.display_name,
    #         )
    #         order = order.sudo()
    #         order.write({'pricelist_id': desired_pl.id})
    #         order._recompute_prices()
    #     return order
