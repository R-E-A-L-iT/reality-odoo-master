# -*- coding: utf-8 -*-

import logging
from odoo import api, models, fields

_logger = logging.getLogger(__name__)

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    reveal_ip_public = fields.Char(store=True, compute='_compute_reveal_ip_public')

    @api.depends('reveal_ip')
    def _compute_reveal_ip_public(self):
        for rec in self:
            rec.reveal_ip_public = rec.sudo().reveal_ip or False

    @api.model
    def create(self, vals):
        lead = super(CrmLead, self).create(vals)
        self._set_company_based_on_visitor_country(lead)
        return lead

    def write(self, vals):
        result = super(CrmLead, self).write(vals)
        if 'visitor_ids' in vals:
            for lead in self:
                self._set_company_based_on_visitor_country(lead)
        return result

    def _set_company_based_on_visitor_country(self, lead):
        """Assign company based on visitor's country: US → R-E-A-L.iT U.S. Inc., Others → R-E-A-L.iT Solutions"""
        company_to_assign = None

        if lead.visitor_ids:
            # Check if any visitor is from the United States
            us_country = self.env.ref('base.us', raise_if_not_found=False)
            _logger.info('>>>>>>>us_country>>>>>:%s', us_country.id if us_country else None)

            if us_country:
                has_us_visitor = any(visitor.country_id.id == us_country.id for visitor in lead.visitor_ids)
                _logger.info('>>>>>>>has_us_visitor>>>:%s', has_us_visitor)

                if has_us_visitor:
                    # US visitor → assign to R-E-A-L.iT U.S. Inc.
                    company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT U.S. Inc.')], limit=1)
                    _logger.info('>>>>>>>Assigning US company>>>:%s', company_to_assign.name if company_to_assign else None)
                else:
                    # Non-US visitor → assign to R-E-A-L.iT Solutions
                    company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
                    _logger.info('>>>>>>>Assigning Solutions company>>>:%s', company_to_assign.name if company_to_assign else None)

        # Fallback: if no visitors or country unknown → default to R-E-A-L.iT Solutions
        if not company_to_assign:
            company_to_assign = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT Solutions')], limit=1)
            _logger.info('>>>>>>>Fallback to Solutions company>>>:%s', company_to_assign.name if company_to_assign else None)

        # Assign the company
        if company_to_assign:
            lead.company_id = company_to_assign.id