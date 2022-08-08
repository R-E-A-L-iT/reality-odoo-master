# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal as cPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager
from odoo.osv import expression
import base64

import logging
_logger = logging.getLogger(__name__)


class QuoteCustomerPortal(cPortal):

    @http.route(["/my/orders/<int:order_id>/ponumber"], type='json', auth="public", website=True)
    def poNumber(self, order_id, ponumber, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        order_sudo.customer_po_number = ponumber

        return

    @http.route(["/my/orders/<int:order_id>/poFile"], type='json', auth="public", website=True)
    def poFile(self, order_id, poFile=False, fileName=False,  access_token=None, **post):
        _logger.info("File Recieved")

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if(poFile == False):
            order_sudo.customer_po_file_name = False
            order_sudo.customer_po_file = False
            return

        _logger.info(str(order_sudo.customer_po_file))
        binFile = poFile.encode('utf-16')
        order_sudo.customer_po_file_name = fileName
        # order_sudo.customer_po_file = poFile
        order_sudo.customer_po_file = binFile
        # base64.b64encode(binFile)
        _logger.info("File Set")
        return

    @ http.route(["/my/orders/<int:order_id>/select"], type='json', auth="public", website=True)
    def select(self, order_id, line_ids, selected,  access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        i = 0
        while(i < len(line_ids)):

            digits = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
            line_id_formated = ""

            for c in line_ids[i]:
                if(c in digits):
                    line_id_formated = line_id_formated + c

            select_sudo = request.env['sale.order.line'].sudo().browse(
                int(line_id_formated))
            if(selected[i] == 'true'):
                select_sudo.selected = 'true'
            else:
                select_sudo.selected = 'false'
            i = i + 1

            if order_sudo != select_sudo.order_id:
                return request.redirect(order_sudo.get_portal_url())

        order_sudo._amount_all()
        results = self._get_portal_order_details(order_sudo)

        results['sale_inner_template'] = request.env['ir.ui.view']._render_template("sale.sale_order_portal_content", {
            'sale_order': order_sudo,
            'report_type': "html",
        })

        return results

    @ http.route(["/my/orders/<int:order_id>/sectionSelect"], type='json', auth="public", website=True)
    def sectionSelect(self, order_id, section_id, line_ids, selected,  access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        i = 0

        digits = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
        section_id_formated = ""
        for c in section_id:
            if(c in digits):
                section_id_formated = section_id_formated + c

        select_sudo = request.env['sale.order.line'].sudo().browse(
            int(section_id_formated))
        if(selected):
            select_sudo.selected = 'true'
        else:
            select_sudo.selected = 'false'

        while(i < len(line_ids)):

            digits = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
            line_id_formated = ""

            for c in line_ids[i]:
                if(c in digits):
                    line_id_formated = line_id_formated + c

            select_sudo = request.env['sale.order.line'].sudo().browse(
                int(line_id_formated))
            if(selected):
                select_sudo.sectionSelected = 'true'
            else:
                select_sudo.sectionSelected = 'false'
            i = i + 1

            if order_sudo != select_sudo.order_id:
                return request.redirect(order_sudo.get_portal_url())

        order_sudo._amount_all()
        results = self._get_portal_order_details(order_sudo)

        results['sale_inner_template'] = request.env['ir.ui.view']._render_template("sale.sale_order_portal_content", {
            'sale_order': order_sudo,
            'report_type': "html",
        })

        return results

    @ http.route(["/my/orders/<int:order_id>/fold/<string:line_id>"], type='json', auth="public", website=True)
    def hideUnhide(self, order_id, line_id, checked,  access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        digits = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
        line_id_formated = ""

        for c in line_id:
            if(c in digits):
                line_id_formated = line_id_formated + c

        select_sudo = request.env['sale.order.line'].sudo().browse(
            int(line_id_formated))
        if(checked):
            select_sudo.hiddenSection = 'yes'
        else:
            select_sudo.hiddenSection = 'no'

        if order_sudo != select_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())

        results = self._get_portal_order_details(order_sudo)
        results['sale_template'] = request.env['ir.ui.view']._render_template("sale.sale_order_portal_content", {
            'sale_order': order_sudo,
            'report_type': "html",
        })

        return results

    @ http.route(["/my/orders/<int:order_id>/changeQuantity/<string:line_id>"], type='json', auth="public", website=True)
    def change_quantity(self, order_id, line_id, quantity, access_token=None, **post):
        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        digits = {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
        line_id_formated = ""

        for c in line_id:
            if(c in digits):
                line_id_formated = line_id_formated + c

        select_sudo = request.env['sale.order.line'].sudo().browse(
            int(line_id_formated))
        select_sudo.product_uom_qty = quantity
        if(quantity <= 0):
            raise UserError(_("Product Quantity Must Be At Least 1"))

        if order_sudo != select_sudo.order_id:
            return request.redirect(order_sudo.get_portal_url())
        order_sudo._amount_all()

        results = self._get_portal_order_details(order_sudo)

        results['sale_inner_template'] = request.env['ir.ui.view']._render_template("sale.sale_order_portal_content", {
            'sale_order': order_sudo,
            'report_type': "html",
        })

        return results
