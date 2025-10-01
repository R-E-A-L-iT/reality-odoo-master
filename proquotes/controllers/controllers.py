# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import base64
import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.http import Response
from odoo.addons.website.controllers import form
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal as cPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.addons.website.controllers.main import Website as WebsiteINH
from odoo.osv import expression
import re
from werkzeug.utils import redirect

_logger = logging.getLogger(__name__)


# class CustomPortalSaleOrder(http.Controller):

#     @http.route(['/my/orders/<int:order_id>'], type='http', auth="public", website=True)
#     def update_requesT_lang(self, sale_order_id, **kwargs):
#         sale_order = request.env['sale.order'].sudo().browse(sale_order_id)

#         # Check if the partner's language is French and set the request language to French
#         if sale_order.partner_id.lang.code == 'fr_CA':
#             request.lang.code = 'fr_CA'
#         else:
#             request.lang = request.lang  # Keep the default website language

#         # Call the default controller or return your own response
#         return request.render("sale.sale_order_portal_content", {'sale_order': sale_order})

class QuoteCustomerPortal(cPortal):
    def validate(string):
        reg = "^[a-zA-Z0-9- ]*$"
        return not (re.search(reg, string) == None)

    def _get_portal_order_details(self, order_sudo):
        return {}

    @http.route(
        ["/my/orders/<int:order_id>/ponumber"], type="json", auth="public", website=True
    )
    def poNumber(self, order_id, ponumber, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        if not self.validate(ponumber):
            return

        order_sudo.customer_po_number = ponumber

        return

    @http.route(
        ["/my/orders/<int:order_id>/select"], type="json", auth="public", website=True
    )
    def select(self, order_id, line_ids, selected, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        i = 0
        # Loop through Line Items
        while i < len(line_ids):
            # Calculate Line Id
            digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
            line_id_formated = ""

            for c in line_ids[i]:
                if c in digits:
                    line_id_formated = line_id_formated + c

            # Confirm Quote is not confirmed
            if str(order_sudo.state) == "sale":
                _logger.info("Locked Quote")
                return request.redirect(order_sudo.get_portal_url())
            _logger.info("Unlocked Quote")

            # Select Line based on line_id_formated
            select_sudo = (
                request.env["sale.order.line"].sudo().browse(int(line_id_formated))
            )

            # Update Line
            if selected[i] == "true":
                select_sudo.selected = "true"
            else:
                select_sudo.selected = "false"
            i = i + 1

            if order_sudo != select_sudo.order_id:
                return request.redirect(order_sudo.get_portal_url())

        order_sudo._compute_tax_totals()
        results = self._get_portal_order_details(order_sudo)

        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results

    @http.route(
        ["/my/orders/<int:order_id>/sectionSelect"],
        type="json",
        auth="public",
        website=True,
    )
    def sectionSelect(
        self, order_id, section_id, line_ids, selected, access_token=None, **post
    ):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        i = 0

        # Calculate Line Id
        digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        section_id_formated = ""
        for c in section_id:
            if c in digits:
                section_id_formated = section_id_formated + c

        select_sudo = (
            request.env["sale.order.line"].sudo().browse(int(section_id_formated))
        )
        if selected:
            select_sudo.selected = "true"
        else:
            select_sudo.selected = "false"

        # Loop through Line Items
        while i < len(line_ids):
            # Calculate Line Id
            digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
            line_id_formated = ""

            for c in line_ids[i]:
                if c in digits:
                    line_id_formated = line_id_formated + c

            select_sudo = (
                request.env["sale.order.line"].sudo().browse(int(line_id_formated))
            )

            # Update Line
            if selected:
                select_sudo.sectionSelected = "true"
            else:
                select_sudo.sectionSelected = "false"
            i = i + 1

            if order_sudo != select_sudo.order_id:
                return request.redirect(order_sudo.get_portal_url())

        order_sudo._compute_tax_totals()
        results = self._get_portal_order_details(order_sudo)

        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results

    @http.route(
        ["/my/orders/<int:order_id>/fold/<string:line_id>"],
        type="json",
        auth="public",
        website=True,
    )
    def hideUnhide(self, order_id, line_id, checked, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        # Calculate Line Id
        digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        line_id_formated = ""

        for c in line_id:
            if c in digits:
                line_id_formated = line_id_formated + c

        select_sudo = (
            request.env["sale.order.line"].sudo().browse(int(line_id_formated))
        )

        # Update Line
        if checked:
            select_sudo.hiddenSection = "yes"
        else:
            select_sudo.hiddenSection = "no"

        if order_sudo != select_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())

        results = self._get_portal_order_details(order_sudo)
        results["sale_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results

    @http.route(
        ["/my/orders/<int:order_id>/changeQuantity/<string:line_id>"],
        type="json",
        auth="public",
        website=True,
    )
    def change_quantity(self, order_id, line_id, quantity, access_token=None, **post):
        # Confirm Access
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return request.redirect("/my")

        if str(order_sudo.state) == "sale":
            _logger.info("Locked Quote")
            order_sudo._compute_tax_totals()
            results = self._get_portal_order_details(order_sudo)

            results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {
                    "sale_order": order_sudo,
                    "report_type": "html",
                },
            )

            return results
        _logger.info("Unlocked Quote")

        # Calculate Line Id
        digits = {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}
        line_id_formated = ""

        for c in line_id:
            if c in digits:
                line_id_formated = line_id_formated + c

        select_sudo = (
            request.env["sale.order.line"].sudo().browse(int(line_id_formated))
        )

        # Update Line
        select_sudo.product_uom_qty = quantity
        if quantity <= 0:
            raise UserError(_("Product Quantity Must Be At Least 1"))

        if order_sudo != select_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())
        order_sudo._compute_tax_totals()

        results = self._get_portal_order_details(order_sudo)

        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )

        return results


    @http.route(['/my/orders/<int:order_id>'], type='http', auth='public', website=True)
    def portal_order_page(self, order_id, access_token=None, **kw):
        if kw.get('user_id'):
            # Set context to skip default quote view logging
            request.env = request.env(context=dict(request.env.context, skip_default_quote_view_log=True))
            
            # Manipulate session to prevent core Odoo's daily tracking
            # Core Odoo checks if 'view_quote_<order_id>' session key exists with today's date
            # By setting it here, we trick core Odoo into thinking the quote was already viewed today
            today = fields.Date.today().isoformat()
            request.session[f'view_quote_{order_id}'] = today
            
        return super().portal_order_page(order_id, access_token=access_token, **kw)

    def _post_view_notification(self, order, viewer_partner):
        recipient_ids = []
        if order.user_id and order.user_id.partner_id:
            recipient_ids.append(order.user_id.partner_id.id)

        order.with_context(mail_post_autofollow=True).message_post(
            body=_("Quotation viewed by %s") % viewer_partner.name,
            message_type='comment',
            subtype_xmlid='sale.mt_order_viewed',
            partner_ids=list(set(recipient_ids)),
            author_id=viewer_partner.id,
            subject=_("%s viewed by %s") % (order.name, viewer_partner.name),
        )

    def _log_order_viewed(self, order_sudo):
        if request.params.get('user_id'):
            return
        return super()._log_order_viewed(order_sudo)

    @http.route(['/check_quotation_redirect/<int:order_id>/<string:access_token>'], type='http', auth='public',
                website=True)
    def check_quotation_redirect(self, order_id, access_token, **kwargs):
        if not request.env.user._is_public():
            # Internal user - redirect to backend
            url = f"/web#id={order_id}&model=sale.order&view_type=form"
            return redirect(url)
        else:
            # Portal/public user - handle portal view
            order = request.env['sale.order'].sudo().browse(order_id)
            if order and order.access_token == access_token:
                url = order.get_portal_url()
            else:
                url = '/my'

            user_id = kwargs.get('user_id')
            partner = None
            redirect_url = url

            if user_id:
                try:
                    partner = request.env['res.partner'].sudo().browse(int(user_id))
                    if partner.exists():
                        # Add user_id parameter to the URL
                        sep = '&' if '?' in url else '?'
                        url = f"{url}{sep}user_id={int(user_id)}"
                        
                        # Log the quotation view
                        self._post_view_notification(order, partner)
                        
                        # Set redirect URL with language prefix if needed
                        if partner.lang == 'fr_CA':
                            redirect_url = f"/fr_CA{url}"
                        else:
                            redirect_url = url
                    else:
                        # Partner doesn't exist, use default URL
                        redirect_url = url
                        
                except (ValueError, TypeError):
                    # Invalid user_id, use default URL
                    redirect_url = url
            else:
                # No user_id provided, use default URL
                redirect_url = url

            return redirect(redirect_url)
    
class Website(WebsiteINH):
    # @http.route('/website/lang/<lang>', type='http', auth="public", website=True, multilang=False)
    # def change_lang(self, lang, r='/', **kwargs):
    #     """ :param lang: supposed to be value of `url_code` field """
    #     _logger.info('**********************************',kwargs)
    #     if lang == 'default':
    #         lang = request.website.default_lang_id.url_code
    #         r = '/%s%s' % (lang, r or '/')
    #     lang_code = request.env['res.lang']._lang_get_code(lang)
    #     # replace context with correct lang, to avoid that the url_for of request.redirect remove the
    #     # default lang in case we switch from /fr -> /en with /en as default lang.
    #     _logger.info('>>>>>>>lang_code>>>>>>>',lang_code)
    #     request.update_context(lang=lang_code)
    #     redirect = request.redirect(r or ('/%s' % lang))
    #     redirect.set_cookie(key='frontend_lang', value=str(lang_code), path='/')
        
    #     request.session['lang'] = lang_code
    #     request.env['res.lang']._activate_lang(lang_code)
    #     _logger.info('>>>>>>>lang_code after>>>>>>>:%s',lang_code)
    #     #
    #     _logger.info('>>>>>>>123456789>>>>>>>')
    #     return redirect

    @http.route('/website/lang/<lang>', type='http', auth="public", website=True, multilang=False)
    def change_lang(self, lang, r='/', **kwargs):
        """ :param lang: supposed to be value of `url_code` field """
        if lang == 'default':
            lang = request.website.default_lang_id.url_code
            r = '/%s%s' % (lang, r or '/')
        lang_code = request.env['res.lang']._lang_get_code(lang)
        # replace context with correct lang, to avoid that the url_for of request.redirect remove the
        # default lang in case we switch from /fr -> /en with /en as default lang.
        request.update_context(lang=lang_code)
        redirect = request.redirect(r or ('/%s' % lang))
        redirect.set_cookie('frontend_lang', lang_code)
        return redirect

class QuotePortalFix(cPortal):
    """
    Override to fix duplicate email issue when quotations are accepted and signed through portal.
    
    Problem: The core portal_quote_accept method calls both action_confirm() and _send_order_confirmation_mail()
    which can result in duplicate confirmation emails being sent to followers.
    
    Solution: Remove the redundant _send_order_confirmation_mail() call as the confirmation email
    should be triggered automatically by the order confirmation process.
    """
    
    @http.route(['/my/orders/<int:order_id>/accept'], type='json', auth="public", website=True)
    def portal_quote_accept(self, order_id, access_token=None, name=None, signature=None):
        # get from query string if not on json param
        access_token = access_token or request.httprequest.args.get('access_token')
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'error': _('Invalid order.')}

        if not order_sudo._has_to_be_signed():
            return {'error': _('The order is not in a state requiring customer signature.')}
        if not signature:
            return {'error': _('Signature is missing.')}

        try:
            order_sudo.write({
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signature': signature,
            })
            request.env.cr.commit()
        except (TypeError, binascii.Error) as e:
            return {'error': _('Invalid signature data.')}

        if not order_sudo._has_to_be_paid():
            order_sudo.action_confirm()
            # REMOVED: order_sudo._send_order_confirmation_mail() to fix duplicate email issue

        pdf = request.env['ir.actions.report'].sudo()._render_qweb_pdf('sale.action_report_saleorder', [order_sudo.id])[0]

        _message_post_helper(
            'sale.order',
            order_sudo.id,
            _('Order signed by %s', name),
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
            token=access_token,
        )

        query_string = '&message=sign_ok'
        if order_sudo._has_to_be_paid():
            query_string += '#allow_payment=yes'
        return {
            'force_refresh': True,
            'redirect_url': order_sudo.get_portal_url(query_string=query_string),
        }


class WebsiteForm(form.WebsiteForm):


    # def insert_record(self, request, model, values, custom, meta=None):
    #     if model.model == 'sale.order':
    #         _logger.info('Processing sale.order form submission: %s', values)
            
    #         # Get partner email from form
    #         partner_email = values.get('rental_email') or values.get('email_from') or values.get('email')
    #         partner_name = values.get('partner_name') or partner_email or 'Website Customer'
            
    #         if not partner_email:
    #             raise UserError(_("Email is required for creating quotations."))
            
    #         # Find or create partner
    #         partner = request.env['res.partner'].sudo().search([('email', '=', partner_email)], limit=1)
    #         if not partner:
    #             partner = request.env['res.partner'].sudo().create({
    #                 'name': partner_name,
    #                 'email': partner_email,
    #                 'phone': values.get('phone'),
    #                 'lang': request.context.get('lang', 'en_US'),
    #                 'is_company': False,
    #             })
    #             _logger.info('Created new partner: %s', partner.id)
            
    #         # Update values with partner_id for the sale order creation
    #         values['partner_id'] = partner.id
    #         values['is_rental'] = True
    #         values['is_rental_order'] = True
    #         values['rental_start'] = values.get('rental_start')
    #         values['rental_end'] = values.get('rental_end')
            
    #         # Add company_id if not present
    #         if 'company_id' not in values:
    #             values['company_id'] = request.website.company_id.id
    #         _logger.info('Updated values for sale order: %s', values)
        
    #     # Call parent method to actually create the record
    #     return super().insert_record(request, model, values, custom, meta=meta)



    def insert_record(self, request, model, values, custom, meta=None):
        if model.model == 'sale.order':
            _logger.info('Processing sale.order form submission: %s', values)
            _logger.info('Processing  form custom: %s', custom)
    
            partner_email = values.get('rental_email') or values.get('email_from') or values.get('email')
            partner_name = values.get('partner_name') or partner_email or 'Website Customer'
            company_name = custom.split(":", 1)[-1].strip()
            _logger.info('Processing  form company_name>>>>>>>>>>>: %s', company_name)
            if not partner_email:
                raise UserError(_("Email is required for creating quotations."))
    
            # Find or create/update company contact
            company_partner = request.env['res.partner'].sudo().search([
                ('name', '=', company_name),
                ('is_company', '=', True)
            ], limit=1)
    
            if company_partner:
                _logger.info('Found existing company partner: %s', company_partner.id)
                # Update phone or other details if needed
                company_partner.write({
                    'phone': values.get('company_phone') or company_partner.phone,
                    'email': values.get('company_email') or company_partner.email,
                })
            else:
                company_partner = request.env['res.partner'].sudo().create({
                    'name': company_name,
                    'is_company': True,
                    'phone': values.get('company_phone'),
                    'email': values.get('company_email'),
                    'lang': request.context.get('lang', 'en_US'),
                })
                _logger.info('Created new company partner: %s', company_partner.id)
    
            # Find or create individual contact
            individual_partner = request.env['res.partner'].sudo().search([
                ('email', '=', partner_email),
                ('is_company', '=', False)
            ], limit=1)
    
            if not individual_partner:
                individual_partner = request.env['res.partner'].sudo().create({
                    'name': partner_name,
                    'email': partner_email,
                    'phone': values.get('phone'),
                    'parent_id': company_partner.id,  # Link to company
                    'is_company': False,
                    'lang': request.context.get('lang', 'en_US'),
                })
                _logger.info('Created new individual partner: %s', individual_partner.id)
    
            # Update values for the sale order
            values['partner_id'] = company_partner.id
            values['is_rental'] = True
            values['is_rental_order'] = True
            values['rental_start'] = values.get('rental_start')
            values['rental_end'] = values.get('rental_end')
    
            if 'company_id' not in values:
                values['company_id'] = request.website.company_id.id
    
            _logger.info('Final sale order values: %s', values)
    
        # Create the sale order
        sale_order_result = super().insert_record(request, model, values, custom, meta=meta)
        _logger.info('Created sale_order_result: %s', sale_order_result)
    
        if sale_order_result and model.model == 'sale.order':
            sale_order = request.env['sale.order'].browse(sale_order_result)
    
            # Add individual contact as follower
            if individual_partner and sale_order:
                sale_order.message_subscribe(partner_ids=[individual_partner.id])
                _logger.info('Subscribed individual partner as follower: %s', individual_partner.id)
    
            # Trigger template logic if needed
            if sale_order and sale_order.sale_order_template_id:
                sale_order._onchange_sale_order_template_id()
    
        return sale_order_result