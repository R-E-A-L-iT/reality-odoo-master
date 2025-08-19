# -*- coding: utf-8 -*-
import re
import json
import logging
from datetime import datetime, time

from odoo import http, fields, _
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

            data = {}
            
            if kw:
                data.update(kw)
            
            try:
                raw = request.httprequest.get_data(cache=False, as_text=True)
                if raw:
                    body = json.loads(raw)
                    if isinstance(body, dict):
                        data.update(body)
            except Exception:
                pass

            _logger.info("Rental date update payload for SO %s: %s", order_id, data)

            access_token = data.get('access_token') or data.get('token')
            start_date   = data.get('start_date')   or data.get('start')
            return_date  = data.get('return_date')  or data.get('end')

            user = request.env.user
            has_access = False

            if access_token:
                try:
                    CustomerPortal()._document_check_access('sale.order', order_id, access_token=access_token)
                    has_access = True
                except (AccessError, MissingError):
                    has_access = False

            if not has_access:
                if user.has_group('base.group_user'):
                    has_access = True
                else:
                    partner = user.partner_id.commercial_partner_id
                    has_access = bool(
                        partner and (
                            order.partner_id.commercial_partner_id == partner
                            or partner.id in order.sudo().message_partner_ids.ids
                        )
                    )

            if not has_access:
                return {'ok': False, 'error': 'unauthorized'}

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

            for f in ('rental_start_date', 'rental_return_date'):
                if f in vals and f not in order._fields:
                    return {'ok': False, 'error': f'field_missing:{f}'}

            order.write(vals)
            order.sudo().action_recompute_rental_prices()

            _logger.info("Rental dates updated on SO %s: %s", order.id, vals)

            return {'ok': True}

        except Exception as e:
            _logger.exception("Unexpected error updating rental dates for SO %s", order_id)
            return {'ok': False, 'error': 'exception', 'message': str(e)}

class PortalPONumber(http.Controller):

    @http.route(['/my/orders/<int:order_id>/set_customer_po_number',
         '/my/orders/<int:order_id>/set_customer_po_number/'],
                type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def set_customer_po_number(self, order_id, **kw):
        Order = request.env['sale.order'].sudo()
        order = Order.browse(order_id)
        if not order.exists():
            return {'ok': False, 'error': 'not_found'}

        # Parse payload safely
        data = getattr(request, 'jsonrequest', None) or {}
        if not data:
            try:
                raw = request.httprequest.data or request.httprequest.get_data()
                data = json.loads(raw.decode('utf-8') or '{}') if raw else {}
            except Exception:
                data = {}
        _logger.info("PO number payload for SO %s: %s", order_id, data)

        access_token = data.get('access_token') or data.get('token') or kw.get('access_token')
        customer_po_number    = (data.get('customer_po_number') or '').strip()

        # -------- Access control (token OR logged-in user with access) --------
        user = request.env.user
        has_access = False

        if access_token:
            try:
                CustomerPortal()._document_check_access('sale.order', order_id, access_token=access_token)
                has_access = True
            except (AccessError, MissingError):
                has_access = False

        if not has_access:
            if user.has_group('base.group_user'):
                has_access = True
            else:
                partner = user.partner_id.commercial_partner_id
                has_access = bool(
                    partner and (
                        order.partner_id.commercial_partner_id == partner
                        or partner.id in order.sudo().message_partner_ids.ids
                    )
                )

        if not has_access:
            return {'ok': False, 'error': 'unauthorized'}

        # Optional: enforce max length similar to the field definition
        if len(customer_po_number) > 64:
            customer_po_number = customer_po_number[:64]

        order.write({'customer_po_number': customer_po_number or False})
        _logger.info("PO number updated on SO %s: %s", order.id, customer_po_number)
        return {'ok': True, 'customer_po_number': customer_po_number}