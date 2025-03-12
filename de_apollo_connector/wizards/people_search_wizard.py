# -*- coding: utf-8 -*-

import requests
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class APLPeopleSearchWizard(models.TransientModel):
    _name = "apl.people.search.wizard"
    _description = 'Search People Wizard'

    apl_instance_id = fields.Many2one(
        'apl.instance',
        string='APL Instance',
        default=lambda self: self._compute_default_apl_instance(),
        domain = "[('state','=','active')]"
    )
    job_titles = fields.Char(string='Job Titles')
    org_domains = fields.Char(string='Company Domains')

    page_start = fields.Integer('From Page', default=1, required=True)
    page_last = fields.Integer('Last Page', default=1, required=True)

    result_append = fields.Boolean('Append Results List')

    def _compute_default_apl_instance(self):
        # Find an APL instance record in the current company and return its ID
        apl_instance = self.env['apl.instance'].search([
            ('company_id', '=', self.env.company.id),
            ('state','=','active')
        ], limit=1)  # Limit to one record (if available)

        return apl_instance.id if apl_instance else False

    def get_job_titles_as_array(self):
        return [title.strip() for title in self.job_titles.split(',')]

    def get_org_domains_as_array(self):
        return [title.strip() for title in self.org_domains.split(',')]

    def action_search(self):
        start_page = self.page_start
        last_page = self.page_last
        for i in range(start_page, last_page + 1):
            data = {
                "page" : i,
            }

            if self.job_titles:
                data['person_titles'] = self.get_job_titles_as_array()
    
            if self.org_domains:
                data['q_organization_domains'] = self.get_org_domains_as_array()
                
            #data = json.loads(response.text)
            data = self.apl_instance_id._post_apollo_data('mixed_people/search', data)
            # Check if data is a list, and if it is, assign it to people_data
            if isinstance(data, list):
                people_data = data
            # If data is a dictionary, check if 'people' key exists and assign it to people_data
            elif isinstance(data, dict):
                people_data = data.get('people', [])
                organization_data = data.get('organization', [])
        
            person_values = {}
    
            if not self.result_append:
                self.env['apl.companies'].search([('create_uid', '=', self.env.user.id)]).sudo().unlink()
                self.env['apl.people'].search([('create_uid', '=', self.env.user.id)]).sudo().unlink()
                self.env['apl.people.employment'].search([('create_uid', '=', self.env.user.id)]).sudo().unlink()
            
            for person_data in people_data:
                person_values = {
                    'apl_id': person_data.get('id'),
                    'first_name': person_data.get('first_name'),
                    'last_name': person_data.get('last_name'),
                    'name': person_data.get('name'),
                    'organization_id': person_data.get('organization_id'),
                    'title': person_data.get('title'),
                    'email': person_data.get('email'),
                    'email_status': person_data.get('email_status'),
                    'linkedin_url': person_data.get('linkedin_url'),
                    'twitter_url': person_data.get('twitter_url'),
                    'github_url': person_data.get('github_url'),
                    'facebook_url': person_data.get('facebook_url'),
                    'photo_url': person_data.get('photo_url'),
                    'country': person_data.get('country'),
                    'state': person_data.get('state'),
                    'city': person_data.get('city'),
                    # Map other fields from JSON to your Odoo model fields
                }
                
                person = self.env['apl.people'].create(person_values)
    
                # Organization / Company Date
                organization_data = person_data.get('organization')
                if organization_data:
                    organization_values = {
                        'name': organization_data.get('name'),
                        'website_url': organization_data.get('website_url'),
                        'phone': organization_data.get('phone'),
                        'email': organization_data.get('email'),
                        'blog_url': organization_data.get('blog_url'),
                        'angellist_url': organization_data.get('angellist_url'),
                        'linkedin_url': organization_data.get('linkedin_url'),
                        'linkedin_uid': organization_data.get('linkedin_uid'),
                        'twitter_url': organization_data.get('twitter_url'),
                        'facebook_url': organization_data.get('facebook_url'),
                        'alexa_ranking': organization_data.get('alexa_ranking'),
                        'founded_year': organization_data.get('founded_year'),
                        'logo_url': organization_data.get('logo_url'),
                        'primary_domain': organization_data.get('primary_domain'),
                    }
                    organization = self.env['apl.companies'].create(organization_values)
    
                    # Associate the organization with the person
                    person.write({'apl_people_company_id': organization.id})
                    
    
                # Employement History
                employement_history_ids = person_data.get('employment_history', [])
                for employement_history_id in employement_history_ids:
                    employment_values = {
                        'degree': employement_history_id.get('degree'),
                        'start_date': employement_history_id.get('start_date'),
                        'end_date': employement_history_id.get('end_date'),
                        'grade_level': employement_history_id.get('grade_level'),
                        'kind': employement_history_id.get('kind'),
                        'major': employement_history_id.get('major'),
                        'description': employement_history_id.get('description'),
                        'apl_people_id': person.id,
                    }
                    employement = self.env['apl.people.employment'].create(employment_values)
    
                    # Associate the Employment with the person
                    person.write({'people_employment_history_ids': [(4, employement.id)]})
                    
        # Return an action to open a new form view
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': _('Search Results'),
            'res_model': 'apl.people',
            'domain': [('create_uid', '=', self.env.user.id)],
            'context': {'create': False, 'edit': False},  # Add the context here

        }
        return action


