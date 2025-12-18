import logging 
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = 'website'

    def sale_get_pricelist(self, partner=False):
        self.ensure_one()

        # If we are not in an HTTP request (backend/cron), fall back safely
        if not request:
            return self.pricelist_id

        # Call parent implementation if it exists (requires website_sale)
        parent = super(Website, self)
        if hasattr(parent, 'sale_get_pricelist'):
            pricelist = parent.sale_get_pricelist(partner=partner)
        else:
            # Fallback: website default pricelist (prevents crash)
            _logger.warning(
                "Parent Website.sale_get_pricelist not found (missing dependency on website_sale?). "
                "Falling back to website.pricelist_id."
            )
            pricelist = self.pricelist_id

        # Do not override if user already selected manually
        if request.session.get('pricelist_selected_manually'):
            _logger.info("Pricelist manually selected earlier — skipping geo override.")
            request.session['website_sale_current_pl'] = pricelist.id
            return pricelist

        # Geo detect (guard against failures / empty dict)
        try:
            visitor = request.website.visitor_geoinfo() or {}
        except Exception:
            visitor = {}
        country_code = visitor.get('country_code')
        _logger.info("Detected visitor country_code: %s", country_code)

        # Find pricelists (prefer env on request)
        env = request.env
        usd_pl = env['product.pricelist'].search([('name', '=', 'USD Pricelist')], limit=1)
        cad_pl = env['product.pricelist'].search([('name', '=', 'CAD Pricelist')], limit=1)

        if country_code == 'US' and usd_pl:
            pricelist = usd_pl
        elif country_code == 'CA' and cad_pl:
            pricelist = cad_pl

        # Store into session so cart/checkout stays consistent
        request.session['website_sale_current_pl'] = pricelist.id

        return pricelist