# -*- coding: utf-8 -*-
# 2026-06-11 - Brainecrew Apps

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class AddressSelectorPortal(http.Controller):

    def _get_order(self, order_id, access_token=None):
        try:
            order = request.env["sale.order"].sudo().browse(order_id)
            order.check_access_rights("read")
            return order
        except (AccessError, MissingError):
            return None

    @http.route(
        ["/my/orders/<int:order_id>/select_invoice_address"],
        type="json",
        auth="public",
        website=True,
    )
    def select_invoice_address(self, order_id, partner_id=None, access_token=None, **post):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}
        if not partner_id:
            return {"error": "No partner_id provided"}
        partner = request.env["res.partner"].sudo().browse(int(partner_id))
        if not partner.exists():
            return {"error": "Partner not found"}
        order.sudo().partner_invoice_id = partner.id
        return {"success": True}

    @http.route(
        ["/my/orders/<int:order_id>/select_delivery_address"],
        type="json",
        auth="public",
        website=True,
    )
    def select_delivery_address(self, order_id, partner_id=None, access_token=None, **post):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}
        if not partner_id:
            return {"error": "No partner_id provided"}
        partner = request.env["res.partner"].sudo().browse(int(partner_id))
        if not partner.exists():
            return {"error": "Partner not found"}
        order.sudo().partner_shipping_id = partner.id
        return {"success": True}

    @http.route(
        ["/my/orders/<int:order_id>/create_invoice_address"],
        type="json",
        auth="public",
        website=True,
    )
    def create_invoice_address(
        self, order_id, name=None, street=None, city=None,
        state=None, zip=None, country=None, access_token=None, **post
    ):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}

        vals = {
            "type": "invoice",
            "parent_id": order.partner_id.id,
            "name": name or order.partner_id.name,
            "street": street,
            "city": city,
            "zip": zip,
        }
        if country:
            vals["country_id"] = int(country)
        if state:
            vals["state_id"] = int(state)

        new_partner = request.env["res.partner"].sudo().create(vals)
        order.sudo().partner_invoice_id = new_partner.id
        return {
            "success": True,
            "partner_id": new_partner.id,
            "name": new_partner.name or "",
            "street": new_partner.street or "",
            "city": new_partner.city or "",
            "state": new_partner.state_id.name or "",
            "zip": new_partner.zip or "",
            "country": new_partner.country_id.name or "",
        }

    @http.route(
        ["/my/orders/<int:order_id>/create_delivery_address"],
        type="json",
        auth="public",
        website=True,
    )
    def create_delivery_address(
        self, order_id, name=None, street=None, city=None,
        state=None, zip=None, country=None, access_token=None, **post
    ):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}

        vals = {
            "type": "delivery",
            "parent_id": order.partner_id.id,
            "name": name or order.partner_id.name,
            "street": street,
            "city": city,
            "zip": zip,
        }
        if country:
            vals["country_id"] = int(country)
        if state:
            vals["state_id"] = int(state)

        new_partner = request.env["res.partner"].sudo().create(vals)
        order.sudo().partner_shipping_id = new_partner.id
        return {
            "success": True,
            "partner_id": new_partner.id,
            "name": new_partner.name or "",
            "street": new_partner.street or "",
            "city": new_partner.city or "",
            "state": new_partner.state_id.name or "",
            "zip": new_partner.zip or "",
            "country": new_partner.country_id.name or "",
        }
