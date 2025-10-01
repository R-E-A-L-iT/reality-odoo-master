from operator import itemgetter
import logging
from odoo import http
from odoo import fields, http, SUPERUSER_ID, _
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
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
    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        values = {}
        # companies = request.env['res.company'].sudo().search([])
        partner = request.env.user.partner_id
        print('>....................... partner ?????????', partner)
        SaleOrder = request.env['sale.order']
        companies = partner.sudo().portal_companies_ids
        print('>....................... companies ?????????', companies)

        if companies:
            print('>>>>>>>>>>> if ??????????????????????????????')
            companies_all_data = []
            for company in companies:
                print('--company--', company)
                company_data = []

                # Quotation block
                quotation_count = SaleOrder.sudo().search_count(
                    self._prepare_quotations_domain_companywise(partner, company)) \
                    if SaleOrder.check_access_rights('read', raise_exception=False) else 0
                print('>>>>>>>>>>>>>>>>>>>>> quotation_count ??????????????????????????', quotation_count)
                company_data.append({
                    'title': 'Quotations',
                    'url': _('/my/quotes/company/%s') % int(company.id),
                    'placeholder_count': quotation_count,
                })
                print('>>>>>>>>>> quotation_count ???????????????????????', quotation_count)

                # Sale order block
                order_count = SaleOrder.sudo().search_count(self._prepare_orders_domain_companywise(partner, company)) \
                    if SaleOrder.check_access_rights('read', raise_exception=False) else 0
                print('>>>>>>>>>>>> order_count ????????????????????', order_count)
                company_data.append({
                    'title': 'Sales Orders',
                    'url': _('/my/orders/company/%s') % int(company.id),
                    'placeholder_count': order_count,
                })
                print('>>>>>>>>>>>>>>> company_data order count ????????????????????????', company_data)

                # Invoice block
                invoice_count = request.env['account.move'].sudo().search_count(
                    self._get_invoices_domain_companywise(company)) \
                    if request.env['account.move'].check_access_rights('read', raise_exception=False) else 0
                print('>>>>>>>>>>>>>>>>> invoice_count ???????????????????????????????', invoice_count)
                company_data.append({
                    'title': 'Invoices',
                    'url': _('/my/invoices/company/%s') % int(company.id),
                    'placeholder_count': invoice_count,
                })
                print('>>>>>>>>>>>>>>> company_data dffd ????????????????????????', company_data)

                # Tickets Block
                ticket_count = request.env['helpdesk.ticket'].sudo().search_count(
                    self._prepare_helpdesk_tickets_domain_companywise(company)) \
                    if request.env['helpdesk.ticket'].check_access_rights('read', raise_exception=False) else 0
                print('>> ticket_count ?????', ticket_count)
                company_data.append({
                    'title': 'Tickets',
                    'url': _('/my/tickets/company/%s') % int(company.id),
                    'placeholder_count': ticket_count,
                })
                print('>> Company_data ?????', company_data)

                # Rental Products
                # rental_orders = request.env['sale.order'].sudo().search(self._prepare_rental_orders_domain_companywise(partner, company))
                #     # if request.env['sale.order'].check_access_rights('read', raise_exception=False) else 0
                # if rental_orders:
                #     rental_product_count = len(rental_orders.mapped('order_line').mapped('product_id').ids)
                # else:
                #     rental_product_count = 0
                # company_data.append({
                #     'title': 'Rental Products',
                #     'url': _('/my/rental/products/company/%s') % int(company.id),
                #     'placeholder_count': rental_product_count,
                # })

                # Pass all blocks to list of that company
                companies_all_data.append({
                    'company_name': company.name,
                    'company_data': company_data
                })
            values['companies'] = companies_all_data
            print('>> Company ?????', values['companies'])
        else:
            print('>>>>>>>>>>> else ??????????????????????????????')
            values['companies'] = False

        # print('>>>>>>>>>>>>>>... sdddds ???????????????????',
        #       request.render("proportal_portal_extension.portal_my_home_company_wise", values))
        return request.render("proportal.portal_my_home_company_wise", values)

    @http.route(['/my/quotes', '/my/quotes/company/<int:partner_company_id>', '/my/quotes/company/<int:partner_company_id>/page/<int:page>', '/my/quotes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_quotes(self, partner_company_id=None, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        if partner_company_id is not None:
            company = request.env['res.partner'].sudo().browse(int(partner_company_id))
            domain = self._prepare_quotations_domain_companywise(partner=partner, company=company)
            quote_url = _("/my/quotes/company/%s") % str(company.id)
            values['partner_company_id'] = int(partner_company_id)
        else:
            domain = self._prepare_quotations_domain(partner)
            quote_url = "/my/quotes"
            values['partner_company_id'] = False

        searchbar_sortings = self._get_sale_searchbar_sortings()

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        quotation_count = SaleOrder.sudo().search_count(domain)
        # make pager
        pager = portal_pager(
            url=quote_url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        quotations = SaleOrder.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_quotations_history'] = quotations.ids[:100]

        values.update({
            'date': date_begin,
            'quotations': quotations.sudo(),
            'page_name': 'quote',
            'pager': pager,
            'default_url': quote_url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        print('>>>>>>>>>>>>>>>. deduct 2.0 ????????????????????',request.render("sale.portal_my_quotations", values))
        return request.render("sale.portal_my_quotations", values)

    @http.route(['/my/orders', '/my/orders/company/<int:partner_company_id>', '/my/orders/company/<int:partner_company_id>/page/<int:page>', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_orders(self, partner_company_id=None, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        if partner_company_id is not None:
            company = request.env['res.partner'].sudo().browse(int(partner_company_id))
            domain = self._prepare_orders_domain_companywise(partner=partner, company=company)
            order_url = _("/my/orders/company/%s") % str(company.id)
            values['partner_company_id'] = int(partner_company_id)
        else:
            domain = self._prepare_orders_domain(partner=partner)
            order_url = "/my/orders"
            values['partner_company_id'] = False

        searchbar_sortings = self._get_sale_searchbar_sortings()

        # default sortby order
        if not sortby:
            sortby = 'date'
        sort_order = searchbar_sortings[sortby]['order']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        order_count = SaleOrder.sudo().search_count(domain)
        # pager
        pager = portal_pager(
            url=order_url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager
        orders = SaleOrder.sudo().search(domain, order=sort_order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_orders_history'] = orders.ids[:100]

        values.update({
            'date': date_begin,
            'orders': orders.sudo(),
            'page_name': 'order',
            'pager': pager,
            'default_url': order_url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        print('>>>>>>>>>>>>>.... deduct 3 ????????????????????',request.render("sale.portal_my_orders", values))
        return request.render("sale.portal_my_orders", values)

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

    @http.route(['/my/invoices/<int:invoice_id>','/my/invoices/company/<int:invoice_id>/<int:partner_company_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, partner_company_id=None, access_token=None, report_type=None, download=False, **kw):
        # try:
        #     invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        # except (AccessError, MissingError):
        #     return request.redirect('/my')

        invoice_sudo = request.env['account.move'].sudo().browse(int(invoice_id))

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=invoice_sudo, report_type=report_type, report_ref='account.account_invoices',
                                     download=download)

        values = self._invoice_get_page_view_values(invoice_sudo, access_token, **kw)
        values['partner_company_id'] = partner_company_id or False
        return request.render("account.portal_invoice_page", values)

    @http.route(['/my/invoices', '/my/invoices/company/<int:partner_company_id>', '/my/invoices/company/<int:partner_company_id>/page/<int:page>', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, partner_company_id=None, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']
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

