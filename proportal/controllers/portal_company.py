from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class ProportalCompanySettings(CustomerPortal):

    @http.route(['/my/company-settings'], type='http', auth='user', website=True)
    def portal_company_settings(self, **kwargs):
        partner = request.env.user.partner_id

        # Only portal administrators see/use this
        if not partner.portal_administrator:
            return request.redirect('/my')

        company_ids = partner.get_portal_company_ids()

        # sudo to read *only* those explicit partners; list is controlled by you
        companies = (request.env['res.partner']
                     .sudo()
                     .browse(company_ids)
                     .exists()
                     .sorted(key=lambda r: r.name or ""))

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'company_settings',
            'companies': companies,
        })
        return request.render('proportal.portal_company_settings', values)