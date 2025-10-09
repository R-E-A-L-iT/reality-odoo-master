# -*- coding: utf-8 -*-

import logging
from odoo import api, models

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
        if lead.visitor_ids:
            us_country = self.env.ref('base.us').id
            _logger.info('>>>>>>>us_country>>>>>25>>:%s',us_country)
            if us_country:
                has_us_visitor = any(visitor.country_id.id == us_country for visitor in lead.visitor_ids)
                _logger.info('>>>>>>>has_us_visitor>>>28>>:%s',has_us_visitor)
                if has_us_visitor:
                    us_company = self.env['res.company'].search([('name', '=', 'R-E-A-L.iT U.S. Inc.')], limit=1)
                    _logger.info('>>>>>>>us_company>>>31>>:%s',us_company)
                    if us_company:
                        lead.company_id = us_company.id