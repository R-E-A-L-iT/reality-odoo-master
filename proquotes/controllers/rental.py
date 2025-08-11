# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)

class PortalRentalDates(http.Controller):

    @http.route(['/my/orders/<int:order_id>/set_rental_dates'],
                type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def set_rental_dates(self, order_id, start_date=None, return_date=None, access_token=None, **kw):
        Order = request.env['sale.order'].sudo()
        order = Order.browse(order_id)
        if not order.exists():
            return {'ok': False, 'error': 'not_found'}

        user = request.env.user

        # 1) If a token was supplied, use the standard portal helper (works for public/portal links)
        if access_token:
            try:
                # Raises on failure; also returns a sudoed record
                CustomerPortal()._document_check_access('sale.order', order_id, access_token=access_token)
                has_access = True
            except (AccessError, MissingError):
                has_access = False
        else:
            has_access = False

        # 2) If no valid token, allow logged-in users with access:
        if not has_access:
            # Internal users always allowed (they have regular ACLs; we still write with sudo for simplicity)
            if user.has_group('base.group_user'):
                has_access = True
            else:
                # Portal users: allow if they can see the order in portal
                # (same logic the portal uses: partner is owner or follower)
                partner = user.partner_id.commercial_partner_id
                has_access = bool(
                    partner
                    and (
                        order.partner_id.commercial_partner_id == partner
                        or partner.id in order.sudo().message_partner_ids.ids
                    )
                )

        if not has_access:
            return {'ok': False, 'error': 'unauthorized'}

        # Parse dates 'YYYY-MM-DD' -> datetimes (start at 00:00, return at 23:59:59)
        def _to_dt(d, end=False):
            if not d:
                return False
            try:
                dd = datetime.fromisoformat(d).date()
            except Exception:
                return False
            base = datetime.combine(dd, time(23, 59, 59) if end else time(0, 0, 0))
            return fields.Datetime.to_string(base)

        vals = {}
        if start_date:
            vals['rental_start_date'] = _to_dt(start_date, end=False)
        if return_date:
            vals['rental_return_date'] = _to_dt(return_date, end=True)

        if not vals:
            return {'ok': False, 'error': 'no_values'}

        try:
            order.write(vals)
            _logger.info("Rental dates updated on SO %s: %s", order.id, vals)
        except Exception as e:
            _logger.exception("Failed writing rental dates on SO %s", order.id)
            return {'ok': False, 'error': 'write_failed'}

        return {'ok': True, 'start_date': vals.get('rental_start_date'), 'return_date': vals.get('rental_return_date')}
