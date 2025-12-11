import logging 
from odoo import models
from odoo.http import request

_logger = logging.getLogger(__name__)

class Website(models.Model):
    _inherit = 'website'

    def sale_get_pricelist(self, partner=False):
        pricelist = super().sale_get_pricelist(partner=partner)

        # Do not override if user already selected manually
        if request.session.get('pricelist_selected_manually'):
            _logger.info("Pricelist manually selected earlier — skipping geo override.")
            return pricelist

        visitor = request.website.visitor_geoinfo()
        country_code = visitor.get('country_code')
        _logger.info("Detected visitor country_code: %s", country_code)

        usd_pl = request.env['product.pricelist'].search([('name', '=', 'USD Pricelist')], limit=1)
        cad_pl = request.env['product.pricelist'].search([('name', '=', 'CAD Pricelist')], limit=1)

        if country_code == 'US' and usd_pl:
            pricelist = usd_pl
        elif country_code == 'CA' and cad_pl:
            pricelist = cad_pl

        # Store into session
        request.session['website_sale_current_pl'] = pricelist.id

        return pricelist