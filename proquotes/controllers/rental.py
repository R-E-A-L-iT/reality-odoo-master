# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# 2026-02-25 - Brainecrew Apps

import logging

from odoo import http
from odoo.exceptions import AccessError, MissingError, UserError, ValidationError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal as cPortal
from odoo.tools.misc import formatLang

from odoo.addons.proquotes.models.rental_portal_dates import (
    normalize_lang_code,
    paid_rental_days,
    rental_calendar_days,
    rental_message,
    validate_portal_rental_pair,
)

_logger = logging.getLogger(__name__)


def portal_lang_code():
    """Website language for portal rental messages (``fr_CA`` vs English)."""
    lang = getattr(request, "lang", None)
    code = normalize_lang_code(lang) if lang else ""
    if code:
        return code
    return request.env.context.get("lang") or "en_US"


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

        lang = portal_lang_code()
        # Validate before any write. A native date input reports each
        # intermediate valid day while the customer is typing; an end day
        # that sorts before the start must not reach the SQL constraint.
        reason = validate_portal_rental_pair(rental_start, rental_end)
        if reason:
            return {"error": rental_message(reason, lang)}

        start_raw = (rental_start or "").strip()
        end_raw = (rental_end or "").strip()
        try:
            start_utc = order_sudo.portal_rental_datetime_utc(start_raw)
            end_utc = order_sudo.portal_rental_datetime_utc(end_raw)
            # The SQL constraint stays the backstop. A failed check is
            # returned as JSON so the portal never shows the raw RPC dialog.
            if start_utc > end_utc:
                return {"error": rental_message("order", lang)}
            order_sudo.sudo().write({
                "rental_start_date": start_utc,
                "rental_return_date": end_utc,
            })
            order_sudo.sudo()._portal_apply_rental_prices()
        except (ValidationError, UserError):
            request.env.cr.rollback()
            _logger.info(
                "Rejected rental dates %s → %s on sale.order %s",
                start_raw, end_raw, order_id,
            )
            return {"error": rental_message("order", lang)}
        except Exception:
            _logger.exception(
                "Failed to update rental dates on sale.order %s", order_id
            )
            request.env.cr.rollback()
            return {"error": rental_message("save", lang)}

        return self._rental_dates_payload(order_sudo)

    def _rental_dates_payload(self, order):
        """Prices and totals after a successful save, for the portal to re-render."""
        cal_days = rental_calendar_days(order.rental_start_date, order.rental_return_date)
        payload = {
            "success": True,
            "rental_start": order.portal_rental_date(order.rental_start_date),
            "rental_end": order.portal_rental_date(order.rental_return_date),
            "paid_days": paid_rental_days(cal_days),
            "order_amount_total": formatLang(
                request.env, order.amount_total, currency_obj=order.currency_id
            ),
        }
        try:
            html = request.env["ir.ui.view"]._render_template(
                "sale.sale_order_portal_content",
                {"sale_order": order, "report_type": "html"},
            )
            payload["sale_inner_template"] = str(html)
        except Exception:
            _logger.exception(
                "Could not re-render portal quote after rental date save on %s",
                order.id,
            )
        return payload