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
            return rec.child_ids.filtered(lambda r: r.type == t)[:1] if rec.child_ids else request.env['res.partner']
        invoice_partner = _first_child_of_type(company, 'invoice')
        delivery_partner = _first_child_of_type(company, 'delivery')
        renewal_partner = _first_child_of_type(company, 'renewal')
        
        # Get countries and states for dropdowns
        countries = request.env['res.country'].sudo().search([]).sorted(key=lambda r: r.name)
        states = request.env['res.country.state'].sudo().search([]).sorted(key=lambda r: r.name)

        values = self._prepare_portal_layout_values()
        values.update({
            'page_name': 'company_settings_detail',
            'company': company,
            'invoice_partner': invoice_partner,
            'delivery_partner': delivery_partner,
            'renewal_partner': renewal_partner or company,
            'countries': countries,
            'states': states,
        })
        return request.render('proportal.portal_company_settings_detail', values)

    @http.route(['/my/company-settings/<int:partner_id>/save-address'], type='http', auth='user', website=True, methods=['POST'], csrf=True)
    def save_company_address(self, partner_id, **post):
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

        address_type = post.get('address_type', '')
        if not address_type:
            return request.redirect(f'/my/company-settings/{partner_id}')

        # Prepare address data
        address_data = {
            'name': post.get('name', ''),
            'email': post.get('email', ''),
            'phone': post.get('phone', ''),
            'street': post.get('street', ''),
            'street2': post.get('street2', ''),
            'city': post.get('city', ''),
            'zip': post.get('zip', ''),
            'parent_id': company.id,
            'is_company': False,
            'type': address_type,
        }

        # Handle state and country
        state_id = post.get('state_id')
        if state_id and state_id.isdigit():
            address_data['state_id'] = int(state_id)
        
        country_id = post.get('country_id')
        if country_id and country_id.isdigit():
            address_data['country_id'] = int(country_id)

        try:
            # Check if address of this type already exists
            existing_address = company.child_ids.filtered(lambda r: r.type == address_type)
            
            if existing_address:
                # Update existing address
                existing_address.sudo().write(address_data)
                request.session['portal_success_message'] = f"{address_type.title()} address updated successfully!"
            else:
                # Create new address
                request.env['res.partner'].sudo().create(address_data)
                request.session['portal_success_message'] = f"{address_type.title()} address created successfully!"
                
        except Exception as e:
            request.session['portal_error_message'] = f"Error saving address: {str(e)}"

        return request.redirect(f'/my/company-settings/{partner_id}')