# -*- coding: utf-8 -*-
# 2026-06-11 - Brainecrew Apps

from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from .address_fields import plan_address_write


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
        self, order_id, address_type=None, name=None, street=None, street2=None,
        city=None, state=None, zip=None, country=None, access_token=None, **post
    ):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}
        if address_type not in ("invoice", "delivery"):
            return {"error": "Invalid address_type"}

        submitted = self._submitted_address(
            name, street, street2, city, state, zip, country
        )
        plan = self._plan_address(submitted, is_create=True)
        if plan["missing"]:
            return self._missing_address_error(plan["missing"])

        vals = dict(plan["vals"])
        if not vals.get("name"):
            vals["name"] = order.partner_id.name or ""
        vals["type"] = address_type
        vals["parent_id"] = order.partner_id.id

        partner = request.env["res.partner"].sudo().create(vals)
        if address_type == "invoice":
            order.sudo().partner_invoice_id = partner.id
        else:
            order.sudo().partner_shipping_id = partner.id

        return self._address_payload(partner)

    @http.route(
        ["/my/orders/<int:order_id>/update_address"],
        type="json",
        auth="public",
        website=True,
    )
    def update_address(
        self, order_id, partner_id=None, name=None, street=None, street2=None,
        city=None, state=None, zip=None, country=None, access_token=None, **post
    ):
        order = self._get_order(order_id, access_token)
        if not order:
            return {"error": "Access denied"}
        if not partner_id:
            return {"error": "No partner_id provided"}

        partner = request.env["res.partner"].sudo().browse(int(partner_id))
        if not partner.exists():
            return {"error": "Partner not found"}
        # The order's own contact is the company's default address and is not
        # editable from the quote preview — customers must create a separate
        # address instead of changing the default company/billing address.
        if partner.id == order.partner_id.id:
            return {"error": "The default address cannot be edited"}

        submitted = self._submitted_address(
            name, street, street2, city, state, zip, country
        )
        plan = self._plan_address(submitted, partner=partner, is_create=False)
        if plan["missing"]:
            return self._missing_address_error(plan["missing"])
        # Keys the client did not send are absent from vals, so an edit cannot
        # blank a stored street2 (or any other field) that was not on the form.
        if plan["vals"]:
            partner.sudo().write(plan["vals"])

        return self._address_payload(partner)

    def _submitted_address(self, name, street, street2, city, state, zip_code, country):
        # None stays None so plan_address_write can tell "not sent" from "".
        return {
            "name": name,
            "street": street,
            "street2": street2,
            "city": city,
            "state": state,
            "zip": zip_code,
            "country": country,
        }

    def _plan_address(self, submitted, partner=None, is_create=False):
        existing = None
        if partner is not None:
            existing = {
                "name": partner.name or "",
                "street": partner.street or "",
                "street2": partner.street2 or "",
                "city": partner.city or "",
                "zip": partner.zip or "",
                "state_id": partner.state_id.id or False,
                "country_id": partner.country_id.id or False,
            }
        return plan_address_write(
            submitted,
            existing,
            is_create=is_create,
            country_exists=self._country_exists,
            country_has_states=self._country_has_states,
            state_matches_country=self._state_matches_country,
        )

    def _country_exists(self, country_id):
        return bool(request.env["res.country"].sudo().browse(int(country_id)).exists())

    def _country_has_states(self, country_id):
        return bool(
            request.env["res.country.state"].sudo().search_count(
                [("country_id", "=", int(country_id))], limit=1
            )
        )

    def _state_matches_country(self, state_id, country_id):
        state = request.env["res.country.state"].sudo().browse(int(state_id))
        return bool(state.exists() and state.country_id.id == int(country_id))

    def _missing_address_error(self, missing):
        return {
            "error": "Please complete the required fields.",
            "fields": missing,
        }

    def _address_payload(self, partner):
        return {
            "success": True,
            "partner_id": partner.id,
            "name": partner.name or "",
            "street": partner.street or "",
            "street2": partner.street2 or "",
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
