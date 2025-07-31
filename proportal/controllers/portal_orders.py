from odoo import http
from odoo.http import request
import random
import string
from datetime import datetime, timedelta
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):

    def _get_orders_domain(self, partner):
        domain = super()._get_orders_domain(partner)
        return ['|'] + domain + [('message_partner_ids', 'in', [partner.id])]

        @http.route(['/my/order/<int:order_id>'], type='http', auth='user', website=True)
        def show_verified_order(self, order_id, **kwargs):
            if not request.session.get(f'quote_verified_{order_id}'):
                return http.redirect_with_hash(f'/my/orders/{order_id}')
            return super().portal_my_order(order_id, **kwargs)

class CustomQuoteAccess(http.Controller):

    @http.route(['/my/orders/<int:order_id>'], type='http', auth='user', website=True)
    def portal_my_order(self, order_id, code=None, **kwargs):
        order = request.env['sale.order'].sudo().browse(order_id)
        partner = request.env.user.partner_id

        # Custom access logic: user must be related to the quote
        allowed_partner_ids = [partner.id]
        if partner.parent_id:
            allowed_partner_ids.append(partner.parent_id.id)
        allowed_partner_ids += partner.portal_companies_ids.ids

        if order.partner_id.id not in allowed_partner_ids and \
           order.message_partner_ids.filtered(lambda p: p.id in allowed_partner_ids) == []:
            return request.render('website.404')

        # Check if code is already validated
        if request.session.get(f'quote_verified_{order_id}') is True:
            return http.redirect_with_hash(f'/my/order/{order_id}')

        # Handle submitted code
        if code:
            session_code = request.session.get(f'quote_code_{order_id}')
            if session_code and code == session_code:
                request.session[f'quote_verified_{order_id}'] = True
                return http.redirect_with_hash(f'/my/order/{order_id}')
            else:
                return request.render("proportal.portal_verify_quote_code", {
                    'order': order,
                    'error': "Invalid code. Please try again.",
                })

        # No code submitted: generate and email a code
        generated_code = ''.join(random.choices(string.digits, k=4))
        request.session[f'quote_code_{order_id}'] = generated_code
        request.session[f'quote_code_expiry_{order_id}'] = (datetime.now() + timedelta(minutes=10)).isoformat()

        # Email the code
        request.env['mail.mail'].sudo().create({
            'subject': "Your Quote Access Code",
            'body_html': f"<p>Your access code is: <strong>{generated_code}</strong></p>",
            'email_to': partner.email,
        }).send()

        return request.render("proportal.portal_verify_quote_code", {
            'order': order,
        })