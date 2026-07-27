# -*- coding: utf-8 -*-

import logging
from odoo import api, models, fields
from odoo.http import request
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    reveal_ip_public = fields.Char(store=True, compute='_compute_reveal_ip_public')

    @api.depends('reveal_ip')
    def _compute_reveal_ip_public(self):
        for rec in self:
            rec.reveal_ip_public = rec.sudo().reveal_ip or False

    # Odoo 19: create is @api.model_create_multi (receives a list of vals dicts).
    @api.model_create_multi
    def create(self, vals_list):
        leads = super(CrmLead, self).create(vals_list)
        for lead in leads:
            self._set_company_based_on_visitor_country(lead)
        return leads

    def write(self, vals):
        result = super(CrmLead, self).write(vals)
        if 'visitor_ids' in vals:
            for lead in self:
                self._set_company_based_on_visitor_country(lead)
        return result

    def _set_company_based_on_visitor_country(self, lead):
        """Assign company based on visitor's country: US → R-E-A-L.iT U.S. Inc., Others → R-E-A-L.iT Solutions"""
        company_to_assign = None
        visitor_country = None

        # Method 1: Check lead's linked visitors (works for existing leads or after visitor linking)
        if lead.visitor_ids:
            visitor_country = lead.visitor_ids[0].country_id
            _logger.info('>>>>>>>Found visitor country from lead.visitor_ids: %s', visitor_country.code if visitor_country else None)

        # Method 2: Get current website visitor from request context (works during form submission)
        if not visitor_country:
            try:
                if request and hasattr(request, 'env'):
                    current_visitor = request.env['website.visitor']._get_visitor_from_request()
                    if current_visitor and current_visitor.country_id:
                        visitor_country = current_visitor.country_id
                        _logger.info('>>>>>>>Found visitor country from request context: %s', visitor_country.code if visitor_country else None)
            except (RuntimeError, AttributeError):
                # No request context available (e.g., called from backend, scheduled action, etc.)
                _logger.debug('No request context available for visitor country detection')

        # Method 3: Check partner's country as additional fallback
        if not visitor_country and lead.partner_id and lead.partner_id.country_id:
            visitor_country = lead.partner_id.country_id
            _logger.info('>>>>>>>Found country from partner: %s', visitor_country.code if visitor_country else None)

        # Now assign company based on the detected country
        if visitor_country:
            us_country = self.env.ref('base.us', raise_if_not_found=False)

            if us_country and visitor_country.id == us_country.id:
                # US visitor → assign to R-E-A-L.iT U.S. Inc.
                company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT U.S. Inc.')], limit=1)
                _logger.info('>>>>>>>Assigning US company: %s', company_to_assign.name if company_to_assign else None)
            else:
                # Non-US visitor → assign to R-E-A-L.iT Solutions
                company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
                _logger.info('>>>>>>>Assigning Solutions company for country %s: %s', visitor_country.code, company_to_assign.name if company_to_assign else None)

        # Fallback: if no country detected → default to R-E-A-L.iT Solutions
        if not company_to_assign:
            company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
            _logger.info('>>>>>>>Fallback to Solutions company (no country detected): %s', company_to_assign.name if company_to_assign else None)

        # Assign the company
        if company_to_assign:
            lead.company_id = company_to_assign.id
            _logger.info('>>>>>>>Successfully assigned company %s to lead %s', company_to_assign.name, lead.id)

    def _notify_by_email_render_layout(self, message, recipients_group, msg_vals=False, render_values=None):
        if self and recipients_group.get('notification_group_name') in ('user', 'group_sale_salesman'):
            self.ensure_one()
            recipients_group = dict(recipients_group)
            recipients_group['has_button_access'] = True
            recipients_group['button_access'] = {
                'url': f'{self.get_base_url()}/web#model=crm.lead&id={self.id}&view_type=form',
                'title': _('View Opportunity') if self.type == 'opportunity' else _('View Lead'),
            }
        return super()._notify_by_email_render_layout(
            message, recipients_group, msg_vals=msg_vals, render_values=render_values
        )