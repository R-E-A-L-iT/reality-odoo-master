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

def _normalize(s):
    if not s:
        return ''
    s = re.sub(r'[^A-Za-z0-9]', '', s).upper()
    return s

def _resolve_country(name_or_code):
    if not name_or_code:
        return False
    Country = request.env['res.country'].sudo()
    code = name_or_code.strip().upper()
    c = Country.search([('code', '=', code)], limit=1)
    if c:
        return c.id
    c = Country.search([('name', '=ilike', name_or_code.strip())], limit=1)
    return c.id or False

def _resolve_state(country_id, name_or_code):
    if not name_or_code or not country_id:
        return False
    State = request.env['res.country.state'].sudo()
    norm = name_or_code.strip().upper()
    st = State.search([('country_id', '=', country_id), ('code', '=', norm)], limit=1)
    if st:
        return st.id
    st = State.search([('country_id', '=', country_id), ('name', '=ilike', name_or_code.strip())], limit=1)
    return st.id or False

def _best_existing_child_match(company_partner, target_vals, address_type):
    Partner = request.env['res.partner'].sudo()
    dom = [('commercial_partner_id', '=', company_partner.commercial_partner_id.id),
           ('parent_id', '!=', False)]
    if address_type in ('invoice', 'delivery'):
        dom = ['|', ('type', '=', address_type), ('type', '=', False)] + dom
    candidates = Partner.search(dom, limit=200)

    t_street  = _normalize(target_vals.get('street'))
    t_street2 = _normalize(target_vals.get('street2'))
    t_city    = _normalize(target_vals.get('city'))
    t_zip     = _normalize(target_vals.get('zip'))
    t_country = _normalize(target_vals.get('country'))
    t_state   = _normalize(target_vals.get('state'))

    best = False
    best_score = 0
    for c in candidates:
        s1 = _normalize(c.street)
        s2 = _normalize(c.street2)
        city = _normalize(c.city)
        zipc = _normalize(c.zip)
        country = _normalize(c.country_id and c.country_id.name or '')
        state = _normalize((c.state_id and c.state_id.code) or (c.state_id and c.state_id.name) or '')

        score = 0
        if zipc and t_zip and zipc == t_zip: score += 3
        if city and t_city and city == t_city: score += 3
        if s1 and t_street and s1 == t_street: score += 2
        if s2 and t_street2 and s2 == t_street2: score += 1
        if country and t_country and country == t_country: score += 1
        if state and t_state and state == t_state: score += 1
        if address_type and (c.type == address_type): score += 1

        if score > best_score:
            best = c
            best_score = score

    return best if best and best_score >= 6 else False

class PortalOrderAddressController(http.Controller):

    @http.route(['/my/orders/<int:order_id>/update_addresses'], type='json', auth='public', website=True, csrf=False)
    def update_addresses(self, order_id, access_token=None, invoice=None, delivery=None, **kw):
        try:
            portal = CustomerPortal()
            rec = portal._document_check_access('sale.order', order_id, access_token=access_token)
            order_sudo = rec[0] if isinstance(rec, (list, tuple)) else rec
            if not order_sudo or not order_sudo.exists():
                return {'ok': False, 'message': 'Order not found or access denied.'}

            def _apply(which, vals):

                if not vals:
                    return None, 'skipped'

                country_id = _resolve_country(vals.get('country'))
                state_id   = _resolve_state(country_id, vals.get('state')) if country_id else False

                def _norm(s): return (s or '').strip()
                target_write = {
                    'name': _norm(vals.get('name')) or '',
                    'street': _norm(vals.get('street')) or '',
                    'street2': _norm(vals.get('street2')) or '',
                    'city': _norm(vals.get('city')) or '',
                    'zip': _norm(vals.get('zip')) or '',
                    'country_id': country_id or False,
                    'state_id': state_id or False,
                }

                addr_type = 'invoice' if which == 'invoice' else 'delivery'
                company_partner = order_sudo.partner_id.commercial_partner_id

                current = (order_sudo.partner_invoice_id if which == 'invoice' else order_sudo.partner_shipping_id).sudo()

                match = _best_existing_child_match(company_partner, vals, addr_type)

                def _changed(cur, payload):
                    return any([
                        _norm(cur.name)   != payload['name'],
                        _norm(cur.street) != payload['street'],
                        _norm(cur.street2)!= payload['street2'],
                        _norm(cur.city)   != payload['city'],
                        _norm(cur.zip)    != payload['zip'],
                        (cur.country_id.id or False) != (payload['country_id'] or False),
                        (cur.state_id.id or False)   != (payload['state_id'] or False),
                    ])

                if match and match.id != current.id:
                    order_sudo.sudo().write({
                        'partner_invoice_id' if which == 'invoice' else 'partner_shipping_id': match.id
                    })
                    return 'switched', f'{which.title()} → existing #{match.id}'

                if current.parent_id:
                    if _changed(current, target_write):
                        current.write(target_write)
                        return 'updated', f'{which.title()} address updated (#{current.id})'
                    return 'unchanged', f'{which.title()} unchanged'

                create_vals = dict(target_write)
                if not create_vals['name']:
                    create_vals['name'] = company_partner.name or 'Address'
                create_vals.update({
                    'parent_id': company_partner.id,
                    'commercial_partner_id': company_partner.id,
                    'type': addr_type,
                    'is_company': False,
                })
                child = request.env['res.partner'].sudo().create(create_vals)

                order_sudo.sudo().write({
                    'partner_invoice_id' if which == 'invoice' else 'partner_shipping_id': child.id
                })
                return 'created', f'{which.title()} child created #{child.id} and set on order'

            inv_status, inv_info = _apply('invoice', invoice or {})
            del_status, del_info = _apply('delivery', delivery or {})

            return {'ok': True, 'info': f'{inv_status or ""} {inv_info or ""} | {del_status or ""} {del_info or ""}'.strip()}

        except Exception as e:
            return {'ok': False, 'message': _('Failed to update addresses.'), 'details': str(e)}

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