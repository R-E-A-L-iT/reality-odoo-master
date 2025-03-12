# -*- coding: utf-8 -*-

import requests
import json

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

class APLCompaniesSearchWizard(models.TransientModel):
    _name = "apl.companies.search.wizard"
    _description = 'Search Companies Wizard'

    apl_instance_id = fields.Many2one('apl.instance', required=True, domain="[('state','=','active')]")
    name = fields.Char(string='Name', )
    job_titles = fields.Char(string='Job Titles')
    company_name = fields.Char(string='Company Name')
    country_id = fields.Many2one('res.country', string='Country')
    state_id = fields.Many2one('res.country.state', string='State', domain="[('country_id', '=', country_id)]")
    city = fields.Char(string='City')
    industry_keywords = fields.Char(string='Industry Keywords')
    no_of_employee = fields.Integer(string='No. of Employees')

    apl_page = fields.Integer('Page', required=True, help="Which page number from apollo to return. Defaults to 1")

    def action_search(self):
        url = self.apl_instance_id.url + 'mixed_people/search'
        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json'
        }
        data = {
            "api_key": self.apl_instance_id.api_key,
            "q_organization_domains": "apollo.io\ngoogle.com",
            "page" : 1,
            "person_titles" : ["sales manager", "engineer manager"]
        }
        response = requests.request("POST", url, headers=headers, json=data)

        #raise UserError(response.text)
        
        data = json.loads(response.text)
        people_data = data.get('people', [])
        
        for person_data in people_data:
            person_values = {
                'apl_id': person_data.get('id'),
                'name': person_data.get('name'),
                'title': person_data.get('title'),
                'email': person_data.get('email'),
                # Map other fields from JSON to your Odoo model fields
            }
            self.env['apl.companies'].search([('uid', '=', self.env.user.id)]).unlink()
            person = self.env['apl.companies'].create(person_values)

        # Return an action to open a new form view
        action = {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'name': _('Search Results'),
            'res_model': 'apl.companies',
        }
        return action


