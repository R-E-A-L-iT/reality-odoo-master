# -*- coding: utf-8 -*-
##############################################################################
#    Copyright (C) 2015 - Present, Braincrew Apps (<http://www.braincrewapps.com>). All Rights Reserved

# Odoo Proprietary License v1.0
#
# This software and associated files (the "Software") may only be used (executed,
# modified, executed after modifications) if you have purchased a valid license
# from the authors, typically via Odoo Apps,  braincrewapps.com, or if you have received a written
# agreement from the authors of the Software.
#
# You may develop Odoo modules that use the Software as a library (typically
# by depending on it, importing it and using its resources), but without copying
# any source code or material from the Software. You may distribute those
# modules under the license of your choice, provided that this license is
# compatible with the terms of the Odoo Proprietary License (For example:
# LGPL, MIT, or proprietary licenses similar to this one).
#
# It is forbidden to publish, distribute, sublicense, or sell copies of the Software
# or modified copies of the Software.
#
# The above copyright notice and this permission notice must be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

##############################################################################
from operator import itemgetter
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


class CustomerPortalReal(CustomerPortal):
    @route(['/my', '/my/home'], type='http', auth="user", website=True)
    def home(self, **kw):
        values = {}
        #companies = request.env['res.company'].sudo().search([])
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']
        companies = partner.sudo().portal_companies

        if companies:
            companies_all_data = []
            for company in companies:
                print(company)
                company_data = []

                # Quotation block
                quotation_count = SaleOrder.sudo().search_count(self._prepare_quotations_domain_companywise(partner, company)) \
                    if SaleOrder.check_access_rights('read', raise_exception=False) else 0
                company_data.append({
                    'title': 'Quotations',
                    'url': _('/my/quotes/company/%s') % int(company.id),
                    'placeholder_count': quotation_count,
                })

                # Sale order block
                order_count = SaleOrder.sudo().search_count(self._prepare_orders_domain_companywise(partner, company)) \
                    if SaleOrder.check_access_rights('read', raise_exception=False) else 0
                company_data.append({
                    'title': 'Sales Orders',
                    'url': _('/my/orders/company/%s') % int(company.id),
                    'placeholder_count': order_count,
                })

                # Invoice block
                invoice_count = request.env['account.move'].sudo().search_count(self._get_invoices_domain_companywise(company)) \
                    if request.env['account.move'].check_access_rights('read', raise_exception=False) else 0
                company_data.append({
                    'title': 'Invoices',
                    'url': _('/my/invoices/company/%s') % int(company.id),
                    'placeholder_count': invoice_count,
                })

                # Tickets Block
                ticket_count = request.env['helpdesk.ticket'].sudo().search_count(self._prepare_helpdesk_tickets_domain_companywise(company)) \
                    if request.env['helpdesk.ticket'].check_access_rights('read', raise_exception=False) else 0
                company_data.append({
                    'title': 'Tickets',
                    'url': _('/my/tickets/company/%s') % int(company.id),
                    'placeholder_count': ticket_count,
                })

                # Rental Products
                rental_orders = request.env['sale.order'].sudo().search(self._prepare_rental_orders_domain_companywise(partner, company))
                    # if request.env['sale.order'].check_access_rights('read', raise_exception=False) else 0
                if rental_orders:
                    rental_product_count = len(rental_orders.mapped('order_line').mapped('product_id').ids)
                else:
                    rental_product_count = 0
                company_data.append({
                    'title': 'Rental Products',
                    'url': _('/my/rental/products/company/%s') % int(company.id),
                    'placeholder_count': rental_product_count,
                })

                # Pass all blocks to list of that company
                companies_all_data.append({
                    'company_name': company.name,
                    'company_data': company_data
                })
            values['companies'] = companies_all_data
        else:
            values['companies'] = False

        return request.render("ba_customer_portal_extension.portal_my_home_company_wise", values)

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
        return request.render("sale.portal_my_orders", values)

    @http.route(['/my/orders/<int:order_id>','/my/orders/company/<int:order_id>/<int:partner_company_id>'], type='http', auth="public", website=True)
    def portal_order_company_page(self, order_id, partner_company_id=None, report_type=None, access_token=None, message=False, download=False, **kw):
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type in ('html', 'pdf', 'text'):
            return self._show_report(model=order_sudo, report_type=report_type,
                                     report_ref='sale.action_report_saleorder', download=download)

        # use sudo to allow accessing/viewing orders for public user
        # only if he knows the private token
        # Log only once a day
        if order_sudo:
            # store the date as a string in the session to allow serialization
            now = fields.Date.today().isoformat()
            session_obj_date = request.session.get('view_quote_%s' % order_sudo.id)
            if session_obj_date != now and request.env.user.share and access_token:
                request.session['view_quote_%s' % order_sudo.id] = now
                body = _('Quotation viewed by customer %s',
                         order_sudo.partner_id.name if request.env.user._is_public() else request.env.user.partner_id.name)
                _message_post_helper(
                    "sale.order",
                    order_sudo.id,
                    body,
                    token=order_sudo.access_token,
                    message_type="notification",
                    subtype_xmlid="mail.mt_note",
                    partner_ids=order_sudo.user_id.sudo().partner_id.ids,
                )

        values = {
            'sale_order': order_sudo,
            'message': message,
            'token': access_token,
            'landing_route': '/shop/payment/validate',
            'bootstrap_formatting': True,
            'partner_id': order_sudo.partner_id.id,
            'report_type': 'html',
            'action': order_sudo._get_portal_return_action(),
        }
        if order_sudo.company_id:
            values['res_company'] = order_sudo.company_id

        values['partner_company_id'] = partner_company_id or False

        # Payment values
        if order_sudo.has_to_be_paid():
            logged_in = not request.env.user._is_public()

            acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
                order_sudo.company_id.id,
                order_sudo.partner_id.id,
                currency_id=order_sudo.currency_id.id,
                sale_order_id=order_sudo.id,
            )  # In sudo mode to read the fields of acquirers and partner (if not logged in)
            tokens = request.env['payment.token'].search([
                ('acquirer_id', 'in', acquirers_sudo.ids),
                ('partner_id', '=', order_sudo.partner_id.id)
            ]) if logged_in else request.env['payment.token']

            # Make sure that the partner's company matches the order's company.
            if not payment_portal.PaymentPortal._can_partner_pay_in_company(
                    order_sudo.partner_id, order_sudo.company_id
            ):
                acquirers_sudo = request.env['payment.acquirer'].sudo()
                tokens = request.env['payment.token']

            fees_by_acquirer = {
                acquirer: acquirer._compute_fees(
                    order_sudo.amount_total,
                    order_sudo.currency_id,
                    order_sudo.partner_id.country_id,
                ) for acquirer in acquirers_sudo.filtered('fees_active')
            }
            # Prevent public partner from saving payment methods but force it for logged in partners
            # buying subscription products
            show_tokenize_input = logged_in \
                                  and not request.env['payment.acquirer'].sudo()._is_tokenization_required(
                sale_order_id=order_sudo.id
            )
            values.update({
                'acquirers': acquirers_sudo,
                'tokens': tokens,
                'fees_by_acquirer': fees_by_acquirer,
                'show_tokenize_input': show_tokenize_input,
                'amount': order_sudo.amount_total,
                'currency': order_sudo.pricelist_id.currency_id,
                'partner_id': order_sudo.partner_id.id,
                'access_token': order_sudo.access_token,
                'transaction_route': order_sudo.get_portal_url(suffix='/transaction'),
                'landing_route': order_sudo.get_portal_url(),
            })

        if order_sudo.state in ('draft', 'sent', 'cancel'):
            history = request.session.get('my_quotations_history', [])
        else:
            history = request.session.get('my_orders_history', [])
        values.update(get_records_pager(history, order_sudo))

        return request.render('sale.sale_order_portal_template', values)

    @http.route(['/my/invoices/<int:invoice_id>','/my/invoices/company/<int:invoice_id>/<int:partner_company_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, partner_company_id=None, access_token=None, report_type=None, download=False, **kw):
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

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

        if partner_company_id is not None:
            company = request.env['res.partner'].sudo().browse(int(partner_company_id))
            domain = self._get_invoices_domain_companywise(company=company)
            order_url = _("/my/invoices/company/%s") % str(company.id)
            values['partner_company_id'] = int(partner_company_id)
        else:
            domain = self._get_invoices_domain()
            order_url = "/my/invoices"
            values['partner_company_id'] = False

        searchbar_sortings = {
            'date': {'label': _('Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'invoices': {'label': _('Invoices'), 'domain': [('move_type', '=', ('out_invoice', 'out_refund'))]},
            'bills': {'label': _('Bills'), 'domain': [('move_type', '=', ('in_invoice', 'in_refund'))]},
        }
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        invoice_count = AccountInvoice.sudo().search_count(domain)
        # pager
        pager = portal_pager(
            url=order_url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        invoices = AccountInvoice.sudo().search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        request.session['my_invoices_history'] = invoices.ids[:100]

        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'default_url': order_url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
        })
        return request.render("account.portal_my_invoices", values)

    @http.route(['/my/tickets', '/my/tickets/company/<int:partner_company_id>', '/my/tickets/company/<int:partner_company_id>/page/<int:page>', '/my/tickets/page/<int:page>'], type='http', auth="user", website=True)
    def my_helpdesk_tickets(self, partner_company_id=None, page=1, date_begin=None, date_end=None, sortby=None, filterby='all', search=None,
                            groupby='none', search_in='content', **kw):
        values = self._prepare_portal_layout_values()

        if partner_company_id is not None:
            company = request.env['res.partner'].sudo().browse(int(partner_company_id))
            domain = self._prepare_helpdesk_tickets_domain_companywise(partner=company)
            ticket_url = _("/my/tickets/company/%s") % str(company.id)
            values['partner_company_id'] = int(partner_company_id)
        else:
            domain = self._prepare_helpdesk_tickets_domain()
            ticket_url = "/my/tickets"
            values['partner_company_id'] = False

        searchbar_sortings = {
            'date': {'label': _('Newest'), 'order': 'create_date desc'},
            'name': {'label': _('Subject'), 'order': 'name'},
            'stage': {'label': _('Stage'), 'order': 'stage_id'},
            'reference': {'label': _('Reference'), 'order': 'id'},
            'update': {'label': _('Last Stage Update'), 'order': 'date_last_stage_update desc'},
        }
        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'assigned': {'label': _('Assigned'), 'domain': [('user_id', '!=', False)]},
            'unassigned': {'label': _('Unassigned'), 'domain': [('user_id', '=', False)]},
            'open': {'label': _('Open'), 'domain': [('close_date', '=', False)]},
            'closed': {'label': _('Closed'), 'domain': [('close_date', '!=', False)]},
            'last_message_sup': {'label': _('Last message is from support')},
            'last_message_cust': {'label': _('Last message is from customer')},
        }
        searchbar_inputs = {
            'content': {'input': 'content', 'label': Markup(_('Search <span class="nolabel"> (in Content)</span>'))},
            'message': {'input': 'message', 'label': _('Search in Messages')},
            'customer': {'input': 'customer', 'label': _('Search in Customer')},
            'id': {'input': 'id', 'label': _('Search in Reference')},
            'status': {'input': 'status', 'label': _('Search in Stage')},
            'all': {'input': 'all', 'label': _('Search in All')},
        }
        searchbar_groupby = {
            'none': {'input': 'none', 'label': _('None')},
            'stage': {'input': 'stage_id', 'label': _('Stage')},
        }

        # default sort by value
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        if filterby in ['last_message_sup', 'last_message_cust']:
            discussion_subtype_id = request.env.ref('mail.mt_comment').id
            messages = request.env['mail.message'].search_read(
                [('model', '=', 'helpdesk.ticket'), ('subtype_id', '=', discussion_subtype_id)],
                fields=['res_id', 'author_id'], order='date desc')
            last_author_dict = {}
            for message in messages:
                if message['res_id'] not in last_author_dict:
                    last_author_dict[message['res_id']] = message['author_id'][0]

            ticket_author_list = request.env['helpdesk.ticket'].search_read(fields=['id', 'partner_id'])
            ticket_author_dict = dict(
                [(ticket_author['id'], ticket_author['partner_id'][0] if ticket_author['partner_id'] else False) for
                 ticket_author in ticket_author_list])

            last_message_cust = []
            last_message_sup = []
            ticket_ids = set(last_author_dict.keys()) & set(ticket_author_dict.keys())
            for ticket_id in ticket_ids:
                if last_author_dict[ticket_id] == ticket_author_dict[ticket_id]:
                    last_message_cust.append(ticket_id)
                else:
                    last_message_sup.append(ticket_id)

            if filterby == 'last_message_cust':
                domain = AND([domain, [('id', 'in', last_message_cust)]])
            else:
                domain = AND([domain, [('id', 'in', last_message_sup)]])

        else:
            domain = AND([domain, searchbar_filters[filterby]['domain']])

        if date_begin and date_end:
            domain = AND([domain, [('create_date', '>', date_begin), ('create_date', '<=', date_end)]])

        # search
        if search and search_in:
            search_domain = []
            if search_in in ('id', 'all'):
                search_domain = OR([search_domain, [('id', 'ilike', search)]])
            if search_in in ('content', 'all'):
                search_domain = OR([search_domain, ['|', ('name', 'ilike', search), ('description', 'ilike', search)]])
            if search_in in ('customer', 'all'):
                search_domain = OR([search_domain, [('partner_id', 'ilike', search)]])
            if search_in in ('message', 'all'):
                discussion_subtype_id = request.env.ref('mail.mt_comment').id
                search_domain = OR([search_domain, [('message_ids.body', 'ilike', search),
                                                    ('message_ids.subtype_id', '=', discussion_subtype_id)]])
            if search_in in ('status', 'all'):
                search_domain = OR([search_domain, [('stage_id', 'ilike', search)]])
            domain = AND([domain, search_domain])

        # pager
        tickets_count = request.env['helpdesk.ticket'].sudo().search_count(domain)
        pager = portal_pager(
            url=ticket_url,
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'search_in': search_in,
                      'search': search, 'groupby': groupby, 'filterby': filterby},
            total=tickets_count,
            page=page,
            step=self._items_per_page
        )

        tickets = request.env['helpdesk.ticket'].sudo().search(domain, order=order, limit=self._items_per_page,
                                                        offset=pager['offset'])
        request.session['my_tickets_history'] = tickets.ids[:100]

        if groupby == 'stage':
            grouped_tickets = [request.env['helpdesk.ticket'].concat(*g) for k, g in
                               groupbyelem(tickets, itemgetter('stage_id'))]
        else:
            grouped_tickets = [tickets]

        values.update({
            'date': date_begin,
            'grouped_tickets': grouped_tickets,
            'page_name': 'ticket',
            'default_url': ticket_url,
            'pager': pager,
            'searchbar_sortings': searchbar_sortings,
            'searchbar_filters': searchbar_filters,
            'searchbar_inputs': searchbar_inputs,
            'searchbar_groupby': searchbar_groupby,
            'sortby': sortby,
            'groupby': groupby,
            'search_in': search_in,
            'search': search,
            'filterby': filterby,
        })
        return request.render("helpdesk.portal_helpdesk_ticket", values)

    @http.route([
        "/helpdesk/ticket/<int:ticket_id>",
        "/helpdesk/ticket/<int:ticket_id>/<int:partner_company_id>/",
        "/helpdesk/ticket/<int:ticket_id>/<access_token>",
        '/my/ticket/<int:ticket_id>',
        "/my/ticket/<int:ticket_id>/<int:partner_company_id>/",
        '/my/ticket/<int:ticket_id>/<access_token>'
    ], type='http', auth="public", website=True)
    def tickets_followup(self, ticket_id=None, partner_company_id=None, access_token=None, **kw):
        try:
            ticket_sudo = self._document_check_access('helpdesk.ticket', ticket_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._ticket_get_page_view_values(ticket_sudo, access_token, **kw)
        values['partner_company_id'] = partner_company_id or False
        return request.render("helpdesk.tickets_followup", values)

    @http.route(['/my/rental/products/company/<int:partner_company_id>',
                 '/my/rental/products/company/<int:partner_company_id>/page/<int:page>'],
                type='http', auth="user", website=True)
    def portal_my_rental_products(self, partner_company_id=None, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        if partner_company_id is not None:
            company = request.env['res.partner'].sudo().browse(int(partner_company_id))
            domain = self._prepare_rental_orders_domain_companywise(partner=partner, company=company)
            quote_url = _("/my/rental/products/company/%s") % str(company.id)
            values['partner_company_id'] = partner_company_id
        else:
            domain = self._prepare_quotations_domain(partner)
            quote_url = "/my/rental/products/"
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
            'page_name': 'rental_product',
            'pager': pager,
            'default_url': quote_url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("ba_customer_portal_extension.portal_my_rental_products", values)

    def _prepare_quotations_domain_companywise(self, partner, company):
        return [
            # ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel']),
            ('partner_id', '=', company.id),
        ]

    def _prepare_orders_domain_companywise(self, partner, company):
        return [
            # ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done']),
            ('partner_id', '=', company.id)
        ]

    def _prepare_rental_orders_domain_companywise(self, partner, company):
        return [
            ('partner_id', '=', company.id),
            ('is_rental_order', '!=', False)
        ]

    def _get_invoices_domain_companywise(self, company):
        return [('state', 'not in', ('cancel', 'draft')), ('is_move_sent', '=', True), ('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')), ('partner_id', '=', company.id)]

    def _prepare_helpdesk_tickets_domain_companywise(self, partner):
        return [('partner_id', '=', partner.id)]
