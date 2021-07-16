# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.osv import expression

class CustomerPortal(CustomerPortal):
    @http.route(["/my/orders/<int:order_id>/select"], type='json', auth="public", website=True)
    def select(self, order_id, line_ids, selected,  access_token=None, **post):

        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        i = 0
        while(i < len(line_ids)):
            select_sudo = request.env['sale.order.line'].sudo().browse(int(line_ids[i]))
            if(selected[i]):
                select_sudo.selected = 'true'
            else:
                select_sudo.selected = 'false'
            i = i + 1
        
            if order_sudo != select_sudo.order_id:
                return request.redirect(order_sudo.get_portal_url())
        
        order_sudo._amount_all()
        results = self._get_portal_order_details(order_sudo)
        results['sale_template'] = request.env['ir.ui.view']._render_template("sale.sale_order_portal_content", {
            'sale_order': order_sudo,
            'report_type': "html",
        })
        
        return results
    
    @http.route(["/my/orders/<int:order_id>/fold/<string:line_id>"], type='json', auth="public", website=True)
    def select(self, order_id, line_id, checked,  access_token=None, **post):

        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        
        digits = {'1', '2', '3', '4', '5', '6', '7', '8', '9'}
        line_id_formated = ""
        
        for c in line_id:
            if(c in digits):
                line_id_formated = line_id_formated + c
        
        select_sudo = request.env['sale.order.line'].sudo().browse(int(line_id_formated))
        if(checked):
            select_sudo.selected = 'yes'
        else:
            select_sudo.selected = 'no'
        
        if order_sudo != select_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())
        
        results = self._get_portal_order_details(order_sudo)
        results['sale_template'] = request.env['ir.ui.view']._render_template("sale.sale_order_portal_content", {
            'sale_order': order_sudo,
            'report_type': "html",
        })
        
        return results