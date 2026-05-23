# -*- coding: utf-8 -*-

import logging
from odoo import api, models
from odoo.http import request


_logger = logging.getLogger(__name__)

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    def _set_company_based_on_visitor_country(self, event):
        """Assign company based on visitor's country: US → R-E-A-L.iT U.S. Inc., Others → R-E-A-L.iT Solutions"""
        company_to_assign = None

        # Try to get visitor from request context (for website appointments)
        try:
            if request and hasattr(request, 'env'):
                visitor = request.env['website.visitor']._get_visitor_from_request()
                if visitor and visitor.country_id:
                    us_country = self.env.ref('base.us', raise_if_not_found=False)
                    _logger.info('>>>>>>>Calendar event - visitor country: %s', visitor.country_id.name)

                    if us_country and visitor.country_id.id == us_country.id:
                        # US visitor → assign to R-E-A-L.iT U.S. Inc.
                        company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT U.S. Inc.')], limit=1)
                        _logger.info('>>>>>>>Assigning US company to calendar event>>>:%s', company_to_assign.name if company_to_assign else None)
                    else:
                        # Non-US visitor → assign to R-E-A-L.iT Solutions
                        company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
                        _logger.info('>>>>>>>Assigning Solutions company to calendar event>>>:%s', company_to_assign.name if company_to_assign else None)
        except Exception as e:
            _logger.warning('>>>>>>>Could not get visitor from request for calendar event: %s', str(e))

        # Fallback: if no visitor or country unknown → default to R-E-A-L.iT Solutions
        if not company_to_assign:
            company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
            _logger.info('>>>>>>>Fallback to Solutions company for calendar event>>>:%s', company_to_assign.name if company_to_assign else None)

        # Assign the company (only if not already set)
        if company_to_assign and not event.company_id:
            event.company_id = company_to_assign.id

    @api.model
    def create(self, vals):
        event = super(CalendarEvent, self).create(vals)

        # Assign company based on visitor location for website appointments
        self._set_company_based_on_visitor_country(event)

        return event
