# -*- coding: utf-8 -*-

import requests
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
import pprint

from urllib.parse import urlparse

class ConvertDataWizard(models.TransientModel):
    _name = "apl.convert.data.wizard"
    _description = 'Convert Apollo Data into Odoo (Wizard)'

    op_name = fields.Char(string='Operation')

    type = fields.Selection([
        ('lead', 'Lead'), ('opportunity', 'Opportunity')], required=True, tracking=15, index=True,
        default=lambda self: 'lead' if self.env['res.users'].has_group('crm.group_use_lead') else 'opportunity')

    @api.model
    def default_get(self, fields):
        res = super(ConvertDataWizard, self).default_get(fields)
        if 'op_name' in self._context:
            res['op_name'] = self._context.get('op_name')
        return res
    
    def action_process(self):
        active_model = self.env.context.get('active_model')
        active_ids = self.env.context.get('active_ids', [])
        record_ids = self.env[active_model].search([('id','in',active_ids)])
        for record in record_ids:
            country_id = self.env['res.country'].search([('name','=',record.country)],limit=1)
            state_id = self.env['res.country.state'].search([('name','=',record.state)],limit=1)
            if self.op_name == 'contacts' and record.status_converted != 'contact':
                vals = {
                    'name': record.name,
                    'function': record.title,
                    'email': record.email,
                    'linkedin_url': record.linkedin_url,
                    'twitter_url': record.twitter_url,
                    'github_url': record.github_url,
                    'facebook_url': record.facebook_url,
                    'photo_url': record.photo_url,
                    'city': record.city,
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'company_type': 'person',
                }
                partner_id = self.env['res.partner'].create(vals)
                partner_id._compute_image()
                if record.apl_people_company_id:
                    comp_vals = {
                        'name': record.apl_people_company_id.name,
                        'email': record.apl_people_company_id.email,
                        'website': record.apl_people_company_id.website_url,
                        'blog_url': record.apl_people_company_id.blog_url,
                        'angellist_url': record.apl_people_company_id.angellist_url,
                        'linkedin_url': record.apl_people_company_id.linkedin_url,
                        'twitter_url': record.apl_people_company_id.twitter_url,
                        #'github_url': record.apl_people_company_id.github_url,
                        'facebook_url': record.apl_people_company_id.facebook_url,
                        'photo_url': record.apl_people_company_id.logo_url,
                        'city': record.apl_people_company_id.city,
                        'country_id': country_id.id,
                        'state_id': state_id.id,
                        'company_type': 'company',
                        'founded_year': record.apl_people_company_id.founded_year,
                    }
                    company_partner_id = self.env['res.partner'].create(comp_vals)
                    company_partner_id._compute_image()
                    partner_id.write({
                        'parent_id': company_partner_id.id,
                    })
                record.write({
                    'status_converted': 'contact',
                })
            elif self.op_name == 'leads'  and record.status_converted != 'lead':
                vals = {
                    'name': record.name,
                    'contact_name': record.name,
                    'function': record.title,
                    'email_from': record.email,
                    'city': record.city,
                    'country_id': country_id.id,
                    'state_id': state_id.id,
                    'type': self.type
                }
                lead_id = self.env['crm.lead'].create(vals)
                if record.apl_people_company_id:
                    comp_vals = {
                        'name': record.apl_people_company_id.name,
                        'email': record.apl_people_company_id.email,
                        'website': record.apl_people_company_id.website_url,
                        'blog_url': record.apl_people_company_id.blog_url,
                        'angellist_url': record.apl_people_company_id.angellist_url,
                        'linkedin_url': record.apl_people_company_id.linkedin_url,
                        'twitter_url': record.apl_people_company_id.twitter_url,
                        #'github_url': record.apl_people_company_id.github_url,
                        'facebook_url': record.apl_people_company_id.facebook_url,
                        'photo_url': record.apl_people_company_id.logo_url,
                        'city': record.apl_people_company_id.city,
                        'country_id': country_id.id,
                        'state_id': state_id.id,
                        'company_type': 'company',
                        'founded_year': record.apl_people_company_id.founded_year,
                    }
                    company_partner_id = self.env['res.partner'].create(comp_vals)
                    lead_id.write({
                        'partner_id': company_partner_id.id,
                    })
                record.write({
                    'status_converted': 'lead',
                })

        