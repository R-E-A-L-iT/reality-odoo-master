# -*- coding: utf-8 -*-
import logging
from datetime import datetime, time

from odoo import http, fields
from odoo.http import request
from odoo.exceptions import AccessError, MissingError
from odoo.addons.portal.controllers.portal import CustomerPortal

_logger = logging.getLogger(__name__)

class PortalRentalDates(http.Controller):

    @http.route('/my/orders/<int:order_id>/set_rental_dates',
                type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def set_rental_dates(self, order_id, **kw):
        try:
            Order = request.env['sale.order'].sudo()
            order = Order.browse(order_id)
            if not order.exists():
                return {'ok': False, 'error': 'not_found'}

            # Read raw JSON body robustly
            data = request.jsonrequest or {}
            _logger.info("Rental date update payload for SO %s: %s", order_id, data)

            # Keys from payload
            access_token = data.get('access_token') or data.get('token') or kw.get('access_token')
            start_date   = data.get('start_date')   or data.get('start')   or kw.get('start_date')
            return_date  = data.get('return_date')  or data.get('end')     or kw.get('return_date')

            # -------- Access control (token OR logged-in user with access) --------
            user = request.env.user
            has_access = False

            if access_token:
                try:
                    # Raises AccessError/MissingError if token invalid or record not accessible
                    CustomerPortal()._document_check_access('sale.order', order_id, access_token=access_token)
                    has_access = True
                except (AccessError, MissingError):
                    has_access = False

            if not has_access:
                # Internal users may edit
                if user.has_group('base.group_user'):
                    has_access = True
                else:
                    # Portal user: owner or follower
                    partner = user.partner_id.commercial_partner_id
                    has_access = bool(
                        partner and (
                            order.partner_id.commercial_partner_id == partner
                            or partner.id in order.sudo().message_partner_ids.ids
                        )
                    )

            if not has_access:
                return {'ok': False, 'error': 'unauthorized'}

            # -------- Parse and write --------
            def _to_dt(d, end=False):
                if not d:
                    return False
                try:
                    dd = datetime.fromisoformat(d).date()  # expects 'YYYY-MM-DD'
                except Exception:
                    return False
                base = datetime.combine(dd, time(23, 59, 59) if end else time(0, 0, 0))
                return fields.Datetime.to_string(base)

            vals = {}
            if start_date is not None:
                dt = _to_dt(start_date, end=False)
                if dt:
                    vals['rental_start_date'] = dt
            if return_date is not None:
                dt = _to_dt(return_date, end=True)
                if dt:
                    vals['rental_return_date'] = dt

            if not vals:
                return {'ok': False, 'error': 'no_values', 'received': {'start_date': start_date, 'return_date': return_date}}

            # Make sure fields exist (helps catch typos or missing module)
            for f in ('rental_start_date', 'rental_return_date'):
                if f in vals and f not in order._fields:
                    return {'ok': False, 'error': f'field_missing:{f}'}

            order.write(vals)
            _logger.info("Rental dates updated on SO %s: %s", order.id, vals)
            return {'ok': True, **vals}

        except Exception as e:
            _logger.exception("Unexpected error updating rental dates for SO %s", order_id)
            # Never let an exception bubble to the JSON-RPC "Server Error" – return a clean JSON instead
            return {'ok': False, 'error': 'exception', 'message': str(e)}