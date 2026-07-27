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
# Odoo 19 removed portal.controllers.mail._message_post_helper; post directly on
# the (sudo) record via message_post() instead.
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
    @staticmethod
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

        # Always save PO number regardless of order state
        order_sudo.sudo().write({"customer_po_number": ponumber or ""})

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
        if not kw.get('user_id'):
            request.env = request.env(context=dict(request.env.context, skip_default_quote_view_log=True))
            
            # Manipulate session to prevent core Odoo's daily tracking
            # Core Odoo checks if 'view_quote_<order_id>' session key exists with today's date
            # By setting it here, we trick core Odoo into thinking the quote was already viewed today
            today = fields.Date.today().isoformat()
            request.session[f'view_quote_{order_id}'] = today

        return super().portal_order_page(order_id, access_token=access_token, **kw)


    def _post_view_notification(self, order, viewer_partner):

        email = (viewer_partner.email or '').strip().lower()
        first_email = re.split(r'[;,]', email)[0].strip() if email else ''
        
        if first_email.endswith('@r-e-a-l.it'):
            _logger.info(
                "Skipping quotation viewed notification for internal partner %s (%s)",
                viewer_partner.id,
                first_email,
            )
            return

        recipient_ids = []
        if order.user_id and order.user_id.partner_id:
            recipient_ids.append(order.user_id.partner_id.id)

        if viewer_partner.parent_id:
            viewer_display = "%s from %s" % (viewer_partner.name, viewer_partner.parent_id.name)
        else:
            viewer_display = viewer_partner.name

        order.with_context(mail_post_autofollow=True).message_post(
            body=_("Quotation viewed by %s") % viewer_display,
            message_type='comment',
            subtype_xmlid='sale.mt_order_viewed',
            partner_ids=list(set(recipient_ids)),
            author_id=viewer_partner.id,
            subject=_("%s viewed by %s") % (order.name, viewer_display),
        )

    def _log_order_viewed(self, order_sudo):
        if not request.params.get('user_id'):
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
                        elif partner.lang == 'es_ES':
                            redirect_url = f"/es_ES{url}"
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

        order_sudo.message_post(
            body=_('Order signed by %s', name),
            attachments=[('%s.pdf' % order_sudo.name, pdf)],
        )

        query_string = '&message=sign_ok'
        if order_sudo._has_to_be_paid():
            query_string += '#allow_payment=yes'
        return {
            'force_refresh': True,
            'redirect_url': order_sudo.get_portal_url(query_string=query_string),
        }

    @http.route(['/my/orders/<int:order_id>/add_ccp_line'], type='json', auth="public", website=True)
    def add_ccp_line(self, order_id, access_token=None, scanner_name=None, ccp_type=None, period=None, section_name=None, **kw):
        """
        Add a CCP product line to the order based on scanner name, CCP type, and period.
        Uses scanner configuration to generate search patterns dynamically.
        """
        # Access check
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'success': False, 'error': _('Invalid order or access denied.')}

        # Validate inputs
        if not scanner_name or not ccp_type or not period or not section_name:
            return {'success': False, 'error': _('Missing required parameters.')}

        # Check if order is locked (already confirmed)
        if str(order_sudo.state) in ('sale', 'done', 'cancel'):
            return {
                'success': False,
                'error': _('This order is confirmed and cannot be modified. CCP selection changes are not allowed for confirmed orders.'),
                'order_locked': True
            }

        # Get scanner configuration from section name
        scanner_config = request.env['ccp.scanner.config'].sudo().get_scanner_by_section_name(section_name)

        if not scanner_config:
            # Fallback to legacy hardcoded patterns if scanner config not found
            search_patterns = [
                f"{period} {scanner_name} Laser Scanner CCP {ccp_type}",
                f"{period} {scanner_name} CCP {ccp_type}",
                f"CCP {ccp_type} {scanner_name} {period}",
            ]
        else:
            # Use configured search patterns
            search_patterns = scanner_config.get_search_patterns(ccp_type, period)

        # Search for the CCP product - OPTIMIZED: Single query with OR conditions
        if not search_patterns:
            return {'success': False, 'error': _('No search patterns configured.')}

        # Build domain with OR conditions for all patterns
        domain = []
        for i, pattern in enumerate(search_patterns):
            if i > 0:
                domain.insert(0, '|')  # Add OR operator before each additional pattern
            domain.append(('name', 'ilike', pattern))

        product = request.env['product.product'].sudo().search(domain, limit=1)

        if not product:
            return {
                'success': False,
                'error': _('CCP product not found. Searched for patterns: %s') % ', '.join(search_patterns[:3])
            }

        # Find the section line to insert after - OPTIMIZED: Use ORM search instead of filtered
        section_line = order_sudo.order_line.search([
            ('order_id', '=', order_sudo.id),
            ('name', '=', section_name)
        ], limit=1)

        if not section_line:
            return {'success': False, 'error': _('Section not found in order.')}

        # Remove any existing CCP line for this section
        existing_ccp_lines = order_sudo.order_line.search([
            ('order_id', '=', order_sudo.id),
            ('product_id.name', 'ilike', 'CCP'),
            ('product_id.name', 'ilike', scanner_name)
        ])
        if existing_ccp_lines:
            existing_ccp_lines.unlink()

        # Sort remaining lines by (sequence, id) — the same order Odoo renders them.
        # Then renumber with 10-step gaps so every line has a unique sequence.
        # This handles the common case where all lines share the same default sequence
        # value, which would otherwise cause the CCP product to land last.
        remaining_lines = order_sudo.order_line.sorted(key=lambda l: (l.sequence, l.id))
        section_ids = list(remaining_lines.ids)
        section_idx = section_ids.index(section_line.id)
        for i, line in enumerate(remaining_lines):
            line.sequence = (i + 1) * 10
        # Place CCP product midway between section (section_idx+1)*10 and the next line (section_idx+2)*10
        ccp_sequence = (section_idx + 1) * 10 + 5

        # Add the new CCP product line
        line_data = {
            'product_id': product.id,
            'name': product.name,
            'product_uom_qty': 1,
            # Odoo 19: sale.order.line uses product_uom_id (not product_uom).
            'product_uom_id': product.uom_id.id,
            'price_unit': product.list_price,
            'discount': 0,
            'sequence': ccp_sequence,
            'selected': 'true',
            'sectionSelected': 'true',
            'optional': 'no',
            'quantityLocked': 'yes',
            'hiddenSection': 'no',
            'special': 'regular',
            'is_optional': False,
            'is_selected': True,
            'is_quantityLocked': True,
        }

        # Add the line using ORM Command
        from odoo import Command
        order_sudo.write({
            'order_line': [Command.create(line_data)]
        })

        # Get the ID of the newly created line
        new_line = order_sudo.order_line.search([
            ('order_id', '=', order_sudo.id),
            ('product_id', '=', product.id),
            ('sequence', '=', ccp_sequence)
        ], limit=1, order='id desc')

        line_id = f"lineId{new_line.id}" if new_line else None

        # Invalidate ORM cache so the template renders with the freshly written sequences
        order_sudo.invalidate_recordset()

        # Prepare response with updated template
        results = self._get_portal_order_details(order_sudo)
        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )
        results['success'] = True
        results['line_id'] = line_id
        results['product_name'] = product.name

        return results

    @http.route(['/my/orders/<int:order_id>/remove_ccp_line'], type='json', auth="public", website=True)
    def remove_ccp_line(self, order_id, access_token=None, line_id=None, section_name=None, **kw):
        """
        Remove a CCP product line from the order.
        """
        # Access check
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return {'success': False, 'error': _('Invalid order or access denied.')}

        # Check if order is locked (already confirmed)
        if str(order_sudo.state) in ('sale', 'done', 'cancel'):
            return {
                'success': False,
                'error': _('This order is confirmed and cannot be modified. CCP selection changes are not allowed for confirmed orders.'),
                'order_locked': True
            }

        # Extract numeric ID from line_id (format: "lineId123")
        if line_id and line_id.startswith('lineId'):
            numeric_id = int(line_id.replace('lineId', ''))
        else:
            return {'success': False, 'error': _('Invalid line ID format.')}

        # Find and remove the line
        line_to_remove = order_sudo.order_line.filtered(lambda l: l.id == numeric_id)
        if line_to_remove:
            line_to_remove.unlink()
        else:
            return {'success': False, 'error': _('Line not found.')}

        # Recompute tax totals
        order_sudo._compute_tax_totals()

        # Prepare response with updated template
        results = self._get_portal_order_details(order_sudo)
        results["sale_inner_template"] = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {
                "sale_order": order_sudo,
                "report_type": "html",
            },
        )
        results['success'] = True

        return results


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

            # Write address fields to company partner
            address_vals = {}
            if values.get('company_street'):
                address_vals['street'] = values.get('company_street')
            if values.get('company_city'):
                address_vals['city'] = values.get('company_city')
            if values.get('company_zip'):
                address_vals['zip'] = values.get('company_zip')
            state_val = values.get('company_state')
            if state_val:
                try:
                    state = request.env['res.country.state'].sudo().browse(int(state_val))
                    if state.exists():
                        address_vals['state_id'] = state.id
                except (ValueError, TypeError):
                    state = request.env['res.country.state'].sudo().search(
                        [('name', 'ilike', state_val)], limit=1)
                    if state:
                        address_vals['state_id'] = state.id
            country_val = values.get('company_country')
            if country_val:
                try:
                    country = request.env['res.country'].sudo().browse(int(country_val))
                    if country.exists():
                        address_vals['country_id'] = country.id
                except (ValueError, TypeError):
                    country = request.env['res.country'].sudo().search(
                        [('name', 'ilike', country_val)], limit=1)
                    if country:
                        address_vals['country_id'] = country.id
            if address_vals:
                company_partner.write(address_vals)
                _logger.info('Updated company partner address: %s', address_vals)

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
            values['is_rental_order'] = True
            # values['rental_start'] = values.get('rental_start')
            # values['rental_end'] = values.get('rental_end')
    
            if 'company_id' not in values:
                values['company_id'] = request.website.company_id.id
    
            _logger.info('Final sale order values: %s', values)
    
        # Create the sale order
        sale_order_result = super().insert_record(request, model, values, custom, meta=meta)
        _logger.info('Created sale_order_result: %s', sale_order_result)
    
        if sale_order_result and model.model == 'sale.order':
            sale_order = request.env['sale.order'].sudo().browse(sale_order_result)
    
            # Add individual contact as follower
            if individual_partner and sale_order:
                sale_order.message_subscribe(partner_ids=[individual_partner.id])
                _logger.info('Subscribed individual partner as follower: %s', individual_partner.id)
    
            # Trigger template logic if needed
            if sale_order and sale_order.sale_order_template_id:
                sale_order._onchange_sale_order_template_id()
    
        return sale_order_result
