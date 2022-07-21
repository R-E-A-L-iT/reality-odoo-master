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

import logging
_logger = logging.getLogger(__name__)


class RentalCustomerPortal(cPortal):
    @http.route(["/my/orders/<int:order_id>/newAddress"], type='json', auth="public", website=True)
    def newAdd(self, order_id, newAdd, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        order_sudo.rental_diff_add = newAdd

        return

    @http.route(["/my/orders/<int:order_id>/street"], type='json', auth="public", website=True)
    def street(self, order_id, street, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        order_sudo.rental_street = street

        return

    @http.route(["/my/orders/<int:order_id>/city"], type='json', auth="public", website=True)
    def city(self, order_id, city, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        order_sudo.rental_city = city

        return

    @http.route(["/my/orders/<int:order_id>/zip"], type='json', auth="public", website=True)
    def zip(self, order_id, zip, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                'sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        order_sudo.rental_zip = zip

        return
