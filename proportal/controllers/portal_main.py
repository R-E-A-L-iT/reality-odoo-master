from odoo.addons.portal.controllers.portal import CustomerPortal
from operator import itemgetter
import logging
from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.http import content_disposition, Controller, request, route
from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers import portal
from odoo.addons.portal.controllers.portal import pager as portal_pager, get_records_pager
from collections import OrderedDict
from odoo.osv.expression import OR, AND
from markupsafe import Markup
from odoo.tools import groupby as groupbyelem

_logger = logging.getLogger(__name__)


class CustomerPortalReal(CustomerPortal):

    @http.route(['/my/orders/<int:order_id>','/my/orders/company/<int:order_id>/<int:partner_company_id>'], type='http', auth="public", website=True)
    def portal_order_company_page(self, order_id, partner_company_id=None, report_type=None,downpayment=None, access_token=None, message=False, download=False, **kw):
        # Check if this is custom tracking from proquotes module
        if kw.get('user_id'):
            # Set session to prevent default logging - coordinate with proquotes module
            today = fields.Date.today().isoformat()
            session_key = 'view_quote_%s' % order_id
            request.session[session_key] = today
            _logger.info(f"PROPORTAL: Detected custom tracking for order {order_id}, set session {session_key} = {today}")
        
        # try:
        #     order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        # except (AccessError, MissingError):
        #     return request.redirect('/my')

        order_sudo = request.env['sale.order'].sudo().browse(int(order_id))

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type,
                                     report_ref='sale.action_report_saleorder', download=download)

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day - BUT skip if custom tracking is being used
        if order_sudo:
            # store the date as a string in the session to allow serialization
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_quote_%s' % order_sudo.id)
            
            # Only create default log note if NOT from custom tracking (no user_id parameter)
            if not kw.get('user_id') and session_obj_date != now and request.env.user.share and access_token:
                request.session['view_quote_%s' % order_sudo.id] = now
                body = _('Quotation viewed by customer %s',
                         order_sudo.partner_id.name if request.env.user._is_public() else request.env.user.partner_id.name)
                
                _logger.info(f"PROPORTAL: Creating default quote view log for order {order_sudo.id} - NOT from custom tracking")
                
                # Send notification to followers who are internal users
                recipients = []
                sales_email = request.env['res.partner'].sudo().search([('email', '=', 'sales@r-e-a-l.it')], limit=1)
                if sales_email:
                    recipients.append(sales_email.id)

                if order_sudo.user_id and order_sudo.user_id.partner_id:
                    recipients.append(order_sudo.user_id.partner_id.id)

                if recipients:
                    order_sudo.message_post(
                        body=_('Quotation viewed by customer %s') % (
                            order_sudo.partner_id.name if request.env.user._is_public() else request.env.user.partner_id.name),
                        subject="Quotation Viewed",
                        message_type="notification",
                        subtype_xmlid="mail.mt_note",
                        partner_ids=recipients,
                    )
            elif kw.get('user_id'):
                _logger.info(f"PROPORTAL: Skipping default quote view log for order {order_sudo.id} - custom tracking detected")
                
        backend_url = f'/web#model={order_sudo._name}'\
                      f'&id={order_sudo.id}'\
                      f'&action={order_sudo._get_portal_return_action().id}'\
                      f'&view_type=form'


        values = {
            'sale_order': order_sudo,
            'message': message,
            'token': access_token,
            'landing_route': '/shop/payment/validate',
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
            'report_type': 'html',
            'action': order_sudo._get_portal_return_action(),
            'backend_url': backend_url,
        }
        if order_sudo.company_id:
            values['res_company'] = order_sudo.company_id

        values['partner_company_id'] = partner_company_id or False

        # Payment values
        if order_sudo._has_to_be_paid():
            values.update(
                self._get_payment_values(
                    order_sudo,
                    downpayment=downpayment == 'true' if downpayment is not None else order_sudo.prepayment_percent < 1.0
                )
            )

        if order_sudo.state in ('draft', 'sent', 'cancel'):
            history_session_key = 'my_quotations_history'
        else:
            history_session_key = 'my_orders_history'

        values = self._get_page_view_values(
            order_sudo, access_token, values, history_session_key, False)

        return request.render('sale.sale_order_portal_template', values)

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id

        if 'product_count' in counters:
            company_ids = partner.portal_companies_ids.ids
            if partner.parent_id:
                company_ids.append(partner.parent_id.id)

            product_count = request.env['stock.lot'].sudo().search_count([
                ('owner', 'in', company_ids)
            ])
            values['product_count'] = product_count

        return values

