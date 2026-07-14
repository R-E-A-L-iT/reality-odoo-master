from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class ProportalCompanySettings(CustomerPortal):

    def _get_company_partner(self, partner_id):
        """Return the company partner if the current user is allowed to access it."""
        partner = request.env.user.partner_id
        if not partner.portal_administrator:
            return None
        allowed_ids = set(partner.get_portal_company_ids())
        if partner_id not in allowed_ids:
            return None
        company = request.env['res.partner'].sudo().browse(partner_id).exists()
        return company or None

    @http.route(['/my/company-settings'], type='http', auth='user', website=True)
    def portal_company_settings(self, **kwargs):
        partner = request.env.user.partner_id
        if not partner.portal_administrator:
            return request.redirect('/my')

        company_ids = partner.get_portal_company_ids()
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
        company = self._get_company_partner(partner_id)
        if not company:
            return request.redirect('/my/company-settings')

        invoice_addresses  = company.child_ids.filtered(lambda r: r.type == 'invoice'  and r.active)
        delivery_addresses = company.child_ids.filtered(lambda r: r.type == 'delivery' and r.active)
        followup_addresses = company.child_ids.filtered(lambda r: r.type == 'followup' and r.active)
        renewal_addresses  = company.child_ids.filtered(lambda r: r.type == 'renewal'  and r.active)

        ca_codes = ['CA', 'US']
        priority_countries = sorted(
            request.env['res.country'].sudo().search([('code', 'in', ca_codes)]),
            key=lambda c: ca_codes.index(c.code)
        )
        other_countries = request.env['res.country'].sudo().search([('code', 'not in', ca_codes)], order='name asc')
        ca_states    = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'CA')], order='name asc')
        us_states    = request.env['res.country.state'].sudo().search([('country_id.code', '=', 'US')], order='name asc')
        other_states = request.env['res.country.state'].sudo().search([('country_id.code', 'not in', ['CA', 'US'])], order='name asc')

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name':           'company_settings_detail',
            'company':             company,
            'default_partner':     company,
            'invoice_addresses':   invoice_addresses,
            'delivery_addresses':  delivery_addresses,
            'followup_addresses':  followup_addresses,
            'renewal_addresses':   renewal_addresses,
            'priority_countries':  priority_countries,
            'other_countries':     other_countries,
            'ca_states':           ca_states,
            'us_states':           us_states,
            'other_states':        other_states,
        })
        return request.render('proportal.portal_company_settings_detail', values)

    # ── JSON routes for address management ────────────────────────────────────

    @http.route(['/my/company-settings/<int:partner_id>/create_address'],
                type='json', auth='user', website=True)
    def create_company_address(self, partner_id, address_type=None, name=None,
                               street=None, city=None, state=None, zip=None,
                               country=None, **post):
        company = self._get_company_partner(partner_id)
        if not company:
            return {'error': 'Access denied'}
        if address_type not in ('invoice', 'delivery', 'followup', 'renewal'):
            return {'error': 'Invalid address_type'}

        vals = {
            'type':      address_type,
            'parent_id': company.id,
            'name':      name or company.name,
            'street':    street,
            'city':      city,
            'zip':       zip,
        }
        if country:
            vals['country_id'] = int(country)
        if state:
            vals['state_id'] = int(state)

        child = request.env['res.partner'].sudo().create(vals)
        return {
            'success':    True,
            'partner_id': child.id,
            'name':       child.name    or '',
            'street':     child.street  or '',
            'city':       child.city    or '',
            'state':      child.state_id.name or '',
            'zip':        child.zip     or '',
            'country':    child.country_id.name or '',
        }

    @http.route(['/my/company-settings/<int:partner_id>/update_address'],
                type='json', auth='user', website=True)
    def update_company_address(self, partner_id, child_partner_id=None, name=None,
                               street=None, city=None, state=None, zip=None,
                               country=None, **post):
        company = self._get_company_partner(partner_id)
        if not company:
            return {'error': 'Access denied'}
        if not child_partner_id:
            return {'error': 'No child_partner_id provided'}

        child = request.env['res.partner'].sudo().browse(int(child_partner_id))
        if not child.exists() or child.parent_id.id != company.id:
            return {'error': 'Partner not found or not a child of this company'}

        vals = {'name': name, 'street': street, 'city': city, 'zip': zip}
        if country:
            vals['country_id'] = int(country)
        if state:
            vals['state_id'] = int(state)

        child.sudo().write(vals)
        return {
            'success':    True,
            'partner_id': child.id,
            'name':       child.name    or '',
            'street':     child.street  or '',
            'city':       child.city    or '',
            'state':      child.state_id.name or '',
            'zip':        child.zip     or '',
            'country':    child.country_id.name or '',
        }

    @http.route(['/my/company-settings/<int:partner_id>/delete_address'],
                type='json', auth='user', website=True)
    def delete_company_address(self, partner_id, child_partner_id=None, **post):
        company = self._get_company_partner(partner_id)
        if not company:
            return {'error': 'Access denied'}
        if not child_partner_id:
            return {'error': 'No child_partner_id provided'}

        child = request.env['res.partner'].sudo().browse(int(child_partner_id))
        if not child.exists() or child.parent_id.id != company.id:
            return {'error': 'Partner not found or not a child of this company'}

        child.sudo().write({'active': False})
        return {'success': True}
