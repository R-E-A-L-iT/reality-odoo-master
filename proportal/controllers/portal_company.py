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

    @http.route(['/my/company-settings/<int:partner_id>'], type='http', auth='user', website=True)
    def portal_company_settings_detail(self, partner_id, **kwargs):
        # Gate by portal admin flag on the current user's partner
        partner = request.env.user.partner_id
        if not partner.portal_administrator:
            return request.redirect('/my')

        allowed_ids = set(partner.get_portal_company_ids())
        if partner_id not in allowed_ids:
            return request.redirect('/my/company-settings')

        company = request.env['res.partner'].sudo().browse(partner_id).exists()
        if not company:
            return request.redirect('/my/company-settings')

        # You can later wire these to real child contacts; for now, just pass the company
        # and (optionally) derived invoice/delivery contacts if they exist.
        def _first_child_of_type(rec, t):
            return (rec.child_ids.filtered(lambda r: r.type == t)[:1]) or request.env['res.partner']
        invoice_partner = _first_child_of_type(company, 'invoice')
        delivery_partner = _first_child_of_type(company, 'delivery')

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'company_settings_detail',
            'company': company,
            'invoice_partner': invoice_partner,
            'delivery_partner': delivery_partner,
            # For now we just use the company as a fallback for follow-up & renewal displays
            'followup_partner': company,
            'renewal_partner': company,
        })
        return request.render('proportal.portal_company_settings_detail', values)