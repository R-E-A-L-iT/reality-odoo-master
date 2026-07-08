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
        ["/my/orders/<int:order_id>/create_typed_address"],
        type="json",
        auth="public",
        website=True,
    )
    def create_typed_address(
        self, order_id, address_type=None, name=None, street=None, city=None,
        state=None, zip=None, country=None, access_token=None, **post
    ):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}
        if address_type not in ("invoice", "delivery"):
            return {"error": "Invalid address_type"}

        vals = {
            "type": address_type,
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

        partner = request.env["res.partner"].sudo().create(vals)
        if address_type == "invoice":
            order.sudo().partner_invoice_id = partner.id
        else:
            order.sudo().partner_shipping_id = partner.id

        return {
            "success": True,
            "partner_id": partner.id,
            "name":    partner.name or "",
            "street":  partner.street or "",
            "city":    partner.city or "",
            "state":   partner.state_id.name or "",
            "zip":     partner.zip or "",
            "country": partner.country_id.name or "",
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
        # Note: partner_id may be the order's own contact — the "Default"
        # card intentionally edits that record directly, since it represents
        # the company's main address rather than a separate child address.

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
        if partner.id == order.partner_id.id:
            # The order's own contact is the fallback address, not a
            # deletable child record — never archive it.
            return {"error": "Cannot delete the default address"}

        was_selected = False
        if address_type == "invoice" and order.partner_invoice_id.id == partner.id:
            order.sudo().partner_invoice_id = order.partner_id.id
            was_selected = True
        elif address_type == "delivery" and order.partner_shipping_id.id == partner.id:
            order.sudo().partner_shipping_id = order.partner_id.id
            was_selected = True

        partner.sudo().write({"active": False})
        return {"success": True, "was_selected": was_selected}
