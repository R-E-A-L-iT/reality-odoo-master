# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 2026-02-25 - Brainecrew Apps

import binascii
from random import sample

import pytz

from odoo import http, _
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

    def _order_timezone(self, order_sudo):
        """Timezone the online date pickers should be interpreted in — the one the
        backend form displays the datetimes in. Prefer the salesperson's tz, then
        the company's, then the request context, then a sane default."""
        return (
            order_sudo.user_id.tz
            or order_sudo.company_id.partner_id.tz
            or request.env.context.get("tz")
            or "America/Toronto"
        )

    def _parse_portal_rental_date(self, date_str, tz_name):
        """Turn a ``YYYY-MM-DD`` picker value into the naive-UTC datetime to store.

        The picker carries no time, so treat it as local midnight in ``tz_name`` and
        convert to UTC. Without this, Odoo writes the date-only string as midnight
        *UTC*, which the tz-aware backend form then renders on the *previous* day
        (e.g. 2026-08-18 shown as "Aug 17 8:00 PM" in EDT)."""
        try:
            naive = datetime.datetime.strptime(date_str.strip(), "%Y-%m-%d")
        except (ValueError, AttributeError):
            return None
        tz = pytz.timezone(tz_name)
        local_midnight = tz.localize(naive)
        return local_midnight.astimezone(pytz.utc).replace(tzinfo=None)

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

        # Don't let a customer edit dates on a confirmed/locked order.
        if str(order_sudo.state) in ("sale", "done", "cancel"):
            return {"error": "Order Locked"}

        tz_name = self._order_timezone(order_sudo)
        values = {}

        if rental_start:
            start_dt = self._parse_portal_rental_date(rental_start, tz_name)
            if start_dt:
                values["rental_start_date"] = start_dt
                # pickup_date defaults to (and tracks) the rental start; keep them in
                # sync on portal edits UNLESS the pickup was independently set, so we
                # don't leave a stale/divergent pickup date in the backend.
                if (
                    not order_sudo.pickup_date
                    or order_sudo.pickup_date == order_sudo.rental_start_date
                ):
                    values["pickup_date"] = start_dt

        if rental_end:
            end_dt = self._parse_portal_rental_date(rental_end, tz_name)
            if end_dt:
                values["rental_return_date"] = end_dt

        if values:
            order_sudo.sudo().write(values)

            # Rental line prices depend on the dates but aren't retriggered by the
            # write; force a scoped recompute so the returned HTML (and the backend)
            # both reflect the new prices.
            if order_sudo.is_rental_order:
                order_sudo.sudo()._recompute_rental_prices()

            order_sudo._compute_tax_totals()

        # Return the freshly rendered portal content so the frontend can swap it in
        # and show the recalculated prices/totals instantly (no reload).
        sale_inner_template = request.env["ir.ui.view"]._render_template(
            "sale.sale_order_portal_content",
            {"sale_order": order_sudo, "report_type": "html"},
        )

        return {
            "success": True,
            "sale_inner_template": sale_inner_template,
            "order_amount_total": order_sudo.amount_total,
        }