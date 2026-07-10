# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 2026-02-25 - Brainecrew Apps

import binascii
from random import sample

from odoo import http, _, registry
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
import re
from odoo.addons.portal.controllers.portal import CustomerPortal as cPortal
import datetime

import logging

_logger = logging.getLogger(__name__)


class RentalCustomerPortal(cPortal):

    @http.route('/rental/address_data', type='json', auth='public', website=True)
    def get_address_data(self):
        countries = request.env['res.country'].sudo().search([], order='name asc')
        states = request.env['res.country.state'].sudo().search([], order='name asc')
        return {
            'countries': [{'id': c.id, 'name': c.name} for c in countries],
            'states': [{'id': s.id, 'name': s.name, 'country_id': s.country_id.id} for s in states],
        }

    @http.route(
        ["/my/orders/<int:order_id>/update_rental_dates"],
        type="json",
        auth="public",
        website=True,
    )
    def update_rental_dates(self, order_id, rental_start=None, rental_end=None, access_token=None, **post):

        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return {"error": "Access Denied"}

        values = {}

        if rental_start:
            values["rental_start_date"] = rental_start

        if rental_end:
            values["rental_return_date"] = rental_end

        if values:
            order_sudo.sudo().write(values)

            # Auto-update rental prices when dates change
            if order_sudo.is_rental_order and order_sudo.has_rented_products:
                order_sudo.sudo()._recompute_rental_prices()

        return {"success": True}

    @http.route(
        ["/my/orders/<int:order_id>/request_rental_dates"],
        type="json",
        auth="public",
        website=True,
    )
    def request_rental_dates(self, order_id, access_token=None, **post):
        """Customer pressed "Request dates": post the salesperson-tagged
        availability note on the order's chatter."""
        try:
            order_sudo = self._document_check_access(
                "sale.order", order_id, access_token=access_token
            )
        except (AccessError, MissingError):
            return {"error": "Access Denied"}

        if not order_sudo.is_rental_order:
            return {"error": "This is not a rental order."}
        if not (order_sudo.rental_start_date and order_sudo.rental_return_date):
            return {"error": "Please set both rental dates first."}

        order_sudo.sudo()._notify_rental_dates_requested()
        return {"success": True}