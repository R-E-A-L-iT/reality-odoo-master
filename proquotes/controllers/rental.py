# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 2026-02-25 - Brainecrew Apps


from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal as cPortal

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
        ["/my/orders/<int:order_id>/update_invoice_address"],
        type="json",
        auth="public",
        website=True,
    )
    def update_invoice_address(
            self, order_id, name=None, street=None, city=None,
            state=None, zip=None, country=None,
            access_token=None, **post
    ):
        try:
            order_sudo = request.env["sale.order"].sudo().browse(order_id)
            order_sudo.check_access_rights("read")
        except (AccessError, MissingError):
            return {"error": "Access denied"}

        address_vals = {
            "name": name,
            "street": street,
            "city": city,
            "zip": zip,
        }

        if country:
            address_vals["country_id"] = int(country)

        if state:
            address_vals["state_id"] = int(state)

        inv = order_sudo.partner_invoice_id

        if inv and inv.id != order_sudo.partner_id.id:
            inv.sudo().write(address_vals)
        else:
            address_vals.update({
                "type": "invoice",
                "parent_id": order_sudo.partner_id.id,
            })
            new_partner = request.env["res.partner"].sudo().create(address_vals)
            order_sudo.partner_invoice_id = new_partner.id

        return {"success": True}

    @http.route(
        ["/my/orders/<int:order_id>/update_delivery_address"],
        type="json",
        auth="public",
        website=True,
    )
    def update_delivery_address(
            self, order_id, name=None, street=None, city=None,
            state=None, zip=None, country=None,
            access_token=None, **post
    ):
        try:
            order_sudo = request.env["sale.order"].sudo().browse(order_id)
            order_sudo.check_access_rights("read")
        except (AccessError, MissingError):
            return {"error": "Access denied"}

        address_vals = {
            "name": name,
            "street": street,
            "city": city,
            "zip": zip,
        }

        if country:
            address_vals["country_id"] = int(country)

        if state:
            address_vals["state_id"] = int(state)

        dlv = order_sudo.partner_shipping_id

        if dlv and dlv.id != order_sudo.partner_id.id:
            dlv.sudo().write(address_vals)
        else:
            address_vals.update({
                "type": "delivery",
                "parent_id": order_sudo.partner_id.id,
            })
            new_partner = request.env["res.partner"].sudo().create(address_vals)
            order_sudo.partner_shipping_id = new_partner.id

        return {"success": True}


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