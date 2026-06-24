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
        ["/my/orders/<int:order_id>/create_address"],
        type="json",
        auth="public",
        website=True,
    )
    def create_address(
        self, order_id, name=None, street=None, city=None,
        state=None, zip=None, country=None, access_token=None, **post
    ):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}

        base_vals = {
            "parent_id": order.partner_id.id,
            "name": name or order.partner_id.name,
            "street": street,
            "city": city,
            "zip": zip,
        }
        if country:
            base_vals["country_id"] = int(country)
        if state:
            base_vals["state_id"] = int(state)

        inv_partner = request.env["res.partner"].sudo().create({**base_vals, "type": "invoice"})
        del_partner = request.env["res.partner"].sudo().create({**base_vals, "type": "delivery"})
        order.sudo().write({
            "partner_invoice_id":  inv_partner.id,
            "partner_shipping_id": del_partner.id,
        })

        def _fmt(p):
            return {
                "partner_id": p.id,
                "name":    p.name or "",
                "street":  p.street or "",
                "city":    p.city or "",
                "state":   p.state_id.name or "",
                "zip":     p.zip or "",
                "country": p.country_id.name or "",
            }

        return {"success": True, "invoice": _fmt(inv_partner), "delivery": _fmt(del_partner)}

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

    @http.route(
        ["/my/orders/<int:order_id>/update_address"],
        type="json",
        auth="public",
        website=True,
    )
    def update_address(
        self, order_id, partner_id=None, name=None, street=None, city=None,
        state=None, zip=None, country=None, access_token=None, **post
    ):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}
        if not partner_id:
            return {"error": "No partner_id provided"}

        partner = request.env["res.partner"].sudo().browse(int(partner_id))
        if not partner.exists():
            return {"error": "Partner not found"}

        vals = {"name": name, "street": street, "city": city, "zip": zip}
        if country:
            vals["country_id"] = int(country)
        if state:
            vals["state_id"] = int(state)

        partner.sudo().write(vals)
        return {
            "success": True,
            "partner_id": partner.id,
            "name": partner.name or "",
            "street": partner.street or "",
            "city": partner.city or "",
            "state": partner.state_id.name or "",
            "zip": partner.zip or "",
            "country": partner.country_id.name or "",
        }

    @http.route(
        ["/my/orders/<int:order_id>/delete_address"],
        type="json",
        auth="public",
        website=True,
    )
    def delete_address(self, order_id, partner_id=None, address_type=None, access_token=None, **post):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}
        if not partner_id:
            return {"error": "No partner_id provided"}

        partner = request.env["res.partner"].sudo().browse(int(partner_id))
        if not partner.exists():
            return {"error": "Partner not found"}

        was_selected = False
        if address_type == "invoice" and order.partner_invoice_id.id == partner.id:
            order.sudo().partner_invoice_id = order.partner_id.id
            was_selected = True
        elif address_type == "delivery" and order.partner_shipping_id.id == partner.id:
            order.sudo().partner_shipping_id = order.partner_id.id
            was_selected = True

        partner.sudo().write({"active": False})
        return {"success": True, "was_selected": was_selected}
