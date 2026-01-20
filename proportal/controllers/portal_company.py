from odoo import http, fields
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
import logging
import json

_logger = logging.getLogger(__name__)


class ProportalCompanySettings(CustomerPortal):

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
        partner = request.env.user.partner_id
        if not partner.portal_administrator:
            return request.redirect('/my')

        allowed_ids = set(partner.get_portal_company_ids())
        if partner_id not in allowed_ids:
            return request.redirect('/my/company-settings')

        company = request.env['res.partner'].sudo().browse(partner_id).exists()
        if not company:
            return request.redirect('/my/company-settings')

        def _first_child_of_type(rec, t):
            return (rec.child_ids.filtered(lambda r: r.type == t)[:1]) or request.env['res.partner']
        invoice_partner = _first_child_of_type(company, 'invoice')
        delivery_partner = _first_child_of_type(company, 'delivery')
        followup_partner = _first_child_of_type(company, 'followup')
        renewal_partner = _first_child_of_type(company, 'renewal')

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'company_settings_detail',
            'company': company,
            'invoice_partner': invoice_partner,
            'delivery_partner': delivery_partner,
            'followup_partner': followup_partner,
            'renewal_partner': renewal_partner,
        })
        return request.render('proportal.portal_company_settings_detail', values)

    @http.route(['/my/company-settings/<int:partner_id>/update-address/<string:address_type>'], type='http', auth='user', methods=['POST'], csrf=True, website=True)
    def portal_update_address(self, partner_id, address_type, **post):
        _logger.info(f"Starting address update - partner_id: {partner_id}, type: {address_type}")
        _logger.info(f"POST data: {post}")

        # Detect if this is an AJAX request
        is_ajax = request.httprequest.headers.get('Accept', '').find('application/json') != -1

        partner = request.env.user.partner_id
        if not partner.portal_administrator:
            _logger.warning("User is not portal administrator")
            if is_ajax:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Not authorized'}),
                    headers=[('Content-Type', 'application/json')]
                )
            return request.redirect('/my/company-settings')

        allowed_ids = set(partner.get_portal_company_ids())
        if partner_id not in allowed_ids:
            _logger.warning(f"Partner ID {partner_id} not in allowed_ids")
            if is_ajax:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Not authorized'}),
                    headers=[('Content-Type', 'application/json')]
                )
            return request.redirect('/my/company-settings')

        company = request.env['res.partner'].sudo().browse(partner_id).exists()
        if not company:
            _logger.warning(f"Company not found for ID {partner_id}")
            if is_ajax:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Company not found'}),
                    headers=[('Content-Type', 'application/json')]
                )
            return request.redirect('/my/company-settings')

        valid_types = ['invoice', 'delivery', 'followup', 'renewal']
        if address_type not in valid_types:
            _logger.warning(f"Invalid address type: {address_type}")
            if is_ajax:
                return request.make_response(
                    json.dumps({'success': False, 'error': 'Invalid address type'}),
                    headers=[('Content-Type', 'application/json')]
                )
            return request.redirect(f'/my/company-settings/{partner_id}')

        try:
            partner_model = request.env['res.partner'].sudo()
            existing_partner = request.env['res.partner']

            if address_type in ['invoice', 'delivery']:
                existing_partner = company.child_ids.filtered(lambda r: r.type == address_type)[:1]
            elif address_type == 'followup':
                existing_partner = company.child_ids.filtered(lambda r: r.type == 'followup')[:1]
            elif address_type == 'renewal':
                existing_partner = company.child_ids.filtered(lambda r: r.type == 'renewal')[:1]

            _logger.info(f"Existing partner: {existing_partner.name if existing_partner else 'None'}")
            _logger.info(f"Company children: {company.child_ids.mapped('name')} (types: {company.child_ids.mapped('type')})")

            vals = {
                'name': post.get('name', '').strip() if post.get('name') else '',
                'email': post.get('email', '').strip() if post.get('email') else '',
                'phone': post.get('phone', '').strip() if post.get('phone') else '',
                'street': post.get('street', '').strip() if post.get('street') else '',
                'street2': post.get('street2', '').strip() if post.get('street2') else '',
                'city': post.get('city', '').strip() if post.get('city') else '',
                'zip': post.get('zip', '').strip() if post.get('zip') else '',
                'parent_id': company.id,
            }

            _logger.info(f"Values to save: {vals}")

            country_name = post.get('country_id', '').strip() if post.get('country_id') else ''
            if country_name:
                country_model = request.env['res.country'].sudo()
                country = country_model.search([('name', '=', country_name)], limit=1)
                if country:
                    vals['country_id'] = country.id

            state_name = post.get('state_id', '').strip() if post.get('state_id') else ''
            if state_name and vals.get('country_id'):
                state_model = request.env['res.country.state'].sudo()
                state = state_model.search([
                    ('name', '=', state_name),
                    ('country_id', '=', vals['country_id'])
                ], limit=1)
                if state:
                    vals['state_id'] = state.id
            elif state_name:
                state_model = request.env['res.country.state'].sudo()
                state = state_model.search([
                    ('name', '=', state_name)
                ], limit=1)
                if state:
                    vals['state_id'] = state.id

            vals['type'] = address_type
            vals['is_company'] = False
            vals['commercial_partner_id'] = company.commercial_partner_id.id

            if existing_partner:
                existing_partner.write(vals)
                _logger.info(f"Updated {address_type} address for company {company.name}")
            else:
                new_partner = partner_model.create(vals)
                _logger.info(f"Created new {address_type} address for company {company.name}")

            # Return JSON for AJAX, redirect for normal form submission
            if is_ajax:
                return request.make_response(
                    json.dumps({
                        'success': True,
                        'message': f'{address_type.capitalize()} address saved successfully',
                        'redirect_url': f'/my/company-settings/{partner_id}'
                    }),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                # For normal form submission, redirect back to the detail page
                return request.redirect(f'/my/company-settings/{partner_id}')

        except Exception as e:
            _logger.error(f"Error updating {address_type} address: {e}")
            import traceback
            _logger.error(f"Traceback: {traceback.format_exc()}")
            if is_ajax:
                return request.make_response(
                    json.dumps({'success': False, 'error': str(e)}),
                    headers=[('Content-Type', 'application/json')]
                )
            else:
                # For normal form submission, redirect back with error
                return request.redirect(f'/my/company-settings/{partner_id}')
