# controllers/portal_rental.py
# -*- coding: utf-8 -*-
from datetime import datetime, time
from odoo import http, fields
from odoo.http import request

class PortalRentalDates(http.Controller):

    @http.route(['/my/orders/<int:order_id>/set_rental_dates'],
                type='json', auth='public', website=True, csrf=False, methods=['POST'])
    def set_rental_dates(self, order_id, start_date=None, return_date=None, access_token=None, **kw):
        Order = request.env['sale.order'].sudo()
        order = Order.browse(order_id)
        if not order.exists():
            return {'ok': False, 'error': 'not_found'}

        # Basic portal security: respect token if present on order
        if order.access_token:
            if not access_token or access_token != order.access_token:
                return {'ok': False, 'error': 'unauthorized'}

        # Parse dates coming as 'YYYY-MM-DD' into datetimes (start at 00:00, return at 23:59:59)
        def _to_dt(d, end=False):
            if not d:
                return False
            # interpret user input as local date; store as UTC-aware datetime string
            try:
                dd = datetime.fromisoformat(d).date()
            except Exception:
                return False
            base = datetime.combine(dd, time(23,59,59) if end else time(0,0,0))
            # Let Odoo handle tz conversion on write; keep naive here
            return fields.Datetime.to_string(base)

        vals = {}
        if start_date:
            vals['rental_start_date'] = _to_dt(start_date, end=False)
        if return_date:
            vals['rental_return_date'] = _to_dt(return_date, end=True)

        if not vals:
            return {'ok': False, 'error': 'no_values'}

        order.write(vals)

        # If you recompute any estimated totals server-side, you can trigger it here, e.g.:
        # order._compute_rental_estimates()

        return {'ok': True, 'start_date': vals.get('rental_start_date'), 'return_date': vals.get('rental_return_date')}
