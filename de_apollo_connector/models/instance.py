# -*- coding: utf-8 -*-

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import html_escape as escape

import requests
import json

from urllib.parse import urlparse


READONLY_FIELD_STATES = {
    state: [('readonly', True)]
    for state in {'verified', 'active'}
}

class ApolloInstance(models.Model):
    _name = 'apl.instance'
    _description = 'Apollo Instance'

    name = fields.Char(string='Name', required=True, readonly=False, states=READONLY_FIELD_STATES)
    api_key = fields.Char(string='API Key', required=True, help='Secret API Key', readonly=False, states=READONLY_FIELD_STATES)
    url = fields.Char(string='URL', required=True, readonly=False, states=READONLY_FIELD_STATES)
    url_sample = fields.Char(default='https://api.apollo.io/api/v1/')
    
    company_id = fields.Many2one('res.company', string='Company', required=True, readonly=True, states=READONLY_FIELD_STATES, default=lambda self: self.env.company)


    state = fields.Selection([
        ('draft', 'Draft'), 
        ('verified', 'Verified'), 
        ('active', 'Active')], 
        string='Status',default='draft', required=True
    )

    # operations fields
    apl_date_import_contacts = fields.Datetime(string='Contacts import date')
    apl_date_import_accounts = fields.Datetime(string='Accounts import date')
    apl_date_import_leads = fields.Datetime(string='Leads import date')

    apl_date_export_contacts = fields.Datetime(string='Contacts export date')
    apl_date_export_leads = fields.Datetime(string='Leads export date')

    def button_draft(self):
        self.write({
            'state':'draft'
        })

    def button_confirm(self):
        self.write({
            'state':'active'
        })
        
    def connection_test(self):
        
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Connection to Apollo successful; explore its capabilities now.'),
                'type': 'warning',
                'sticky': False,  #True/False will display for few seconds if false
            },
        }

        url = self.url + 'auth/health' #"https://api.apollo.io/v1/auth/health"
        querystring = {
            "api_key": self.api_key
        }
        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json'
        }
        response = requests.request("GET", url, headers=headers, params=querystring)
        if response.status_code == 200: 
            self.write({
                'state': 'verified'
            })
            notification['params'].update({
                'title': _('The connection to Apollo was successful.'),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            })
            
        else:
            # The response indicates an error
            error_message = "API connection error. Please check the response."
            raise UserError(error_message)
        return notification

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("You cannot delete a record with a state other than 'draft'.")
        return super(ApolloInstance, self).unlink()

        
    def button_import_labels(self):
        data = {
            #'api_key': 'GbYvCle7WbRW0lFKYXlArw',
        }
        tags_data = self._get_apollo_data('labels', data)
        category_id = self.env['res.partner.category']
        crm_tag_id = self.env['crm.tag']
        for tag in tags_data:
            if isinstance(tag, dict):  # Check if 'tag' is a dictionary
                category_id = self.env['res.partner.category'].search([('apl_id','=',tag.get('id'))],limit=1)
                crm_tag_id = self.env['crm.tag'].search([('apl_id','=',tag.get('id'))],limit=1)
                if tag.get('name'):
                    if category_id:
                        category_id.write({
                            'name': tag.get('name'),
                        })
                    else:
                        self.env['res.partner.category'].create({
                            'name': tag.get('name'),
                            'apl_id': tag.get('id'),
                        })
                    if crm_tag_id:
                        crm_tag_id.write({
                            'name': tag.get('name'),
                        })
                    else:
                        self.env['crm.tag'].create({
                            'name': tag.get('name'),
                            'apl_id': tag.get('id'),
                        })

    def button_import_stages(self):
        data = {}
        stages_data = self._get_apollo_data('opportunity_stages', data)
        #raise UserError(stages_data.get('opportunity_stages', []))
        stage_id = self.env['crm.stage']
        for stage in stages_data.get('opportunity_stages', []):
            if isinstance(stage, dict):  # Check if 'tag' is a dictionary
                stage_id = self.env['crm.stage'].search([('apl_id','=',stage.get('id'))],limit=1)
                if stage.get('name'):
                    if stage_id:
                        stage_id.write({
                            'name': stage.get('name'),
                            'requirements': stage.get('description'),
                            'is_won': stage.get('is_won'),
                        })
                    else:
                        self.env['crm.stage'].create({
                            'name': stage.get('name'),
                            'apl_id': stage.get('id'),
                            'requirements': stage.get('description'),
                            'is_won': stage.get('is_won'),
                        })

                        
    def button_import(self):
        
        context = {
            'default_op_name': self.name,
        }
        return {
            'name': 'Apollo Operations',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'apl.ops.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context,
        }
        #for partner in partners:

    def button_export(self):
        #partners = self.env['res.partner'].search([('active', '=', True), '|', ('apl_id', '=', False), ('apl_date', '<', fields.Datetime.now())])
        if self._context.get('op_name') == 'contacts':
            partner_ids = self.env['res.partner'].search([('active', '=', True),('update_required_for_apollo', '=', True)])
            for partner in partner_ids:
                partner._send_to_apollo(self)
            self.write({
                'apl_date_export_contacts': self.env.cr.now(),
            })
        elif self._context.get('op_name') == 'leads':
            lead_ids = self.env['crm.lead'].search([('active', '=', True),('update_required_for_apollo', '=', True)])
            for lead in lead_ids:
                lead._send_to_apollo(self)
            self.write({
                'apl_date_export_leads': self.env.cr.now(),
            })
            
        #for partner in partners:


    # ---------------------------------------------------------
    # ---------------------- Operations for Apollo ------------
    # ---------------------------------------------------------
    
    @api.model
    def _post_apollo_data(self, api_name, api_data=None):
        """
        Fetch JSON data from a given URL with optional data payload.
        :param url: The URL to send the request to.
        :param data: Optional data to send with the request.
        :return: JSON data received in the response.
        """
        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json'
        }
        try:
            url = self.url + api_name
            #raise UserError(url)
            # Initialize data as an empty dictionary if it's None
            if api_data is None:
                api_data = {}

            # Add the api_key field to the data dictionary
            api_data['api_key'] = self.api_key

            #raise UserError(api_data)
            
            response = requests.request("POST", url, headers=headers, json=api_data)   
            #raise UserError(response.text)
            json_data = json.loads(response.text)
            return json_data

        except requests.exceptions.RequestException as e:
            # Handle any request exceptions
            raise e

        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            raise e

    @api.model
    def _get_apollo_data(self, api_name, api_data=None):
        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json'
        }
        try:
            url = self.url + api_name
            # Initialize data as an empty dictionary if it's None
            if api_data is None:
                api_data = {}

            # Add the api_key field to the data dictionary
            api_data['api_key'] = self.api_key

            response = requests.request("GET", url, headers=headers, params=api_data)
            #raise UserError(response.text)
            json_data = json.loads(response.text)
            return json_data

        except requests.exceptions.RequestException as e:
            # Handle any request exceptions
            raise e

        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            raise e

    @api.model
    def _put_apollo_data(self, api_name, api_data=None):
        headers = {
            'Cache-Control': 'no-cache',
            'Content-Type': 'application/json'
        }
        try:
            url = self.url + api_name
            # Initialize data as an empty dictionary if it's None
            if api_data is None:
                api_data = {}

            # Add the api_key field to the data dictionary
            api_data['api_key'] = self.api_key

            response = requests.request("PUT", url, headers=headers, params=api_data)
            #raise UserError(response.text)
            json_data = json.loads(response.text)
            return json_data

        except requests.exceptions.RequestException as e:
            # Handle any request exceptions
            raise e

        except json.JSONDecodeError as e:
            # Handle JSON decoding errors
            raise e

