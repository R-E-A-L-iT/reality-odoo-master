# -*- coding: utf-8 -*-

from odoo import api, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

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