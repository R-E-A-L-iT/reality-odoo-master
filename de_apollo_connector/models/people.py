# -*- coding: utf-8 -*-

from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import html_escape as escape
import base64
import requests
import json

class ApolloPeople(models.Model):
    _name = 'apl.people'
    _description = 'Apollo People'

    apl_id = fields.Char('ID', readonly=True)
    first_name = fields.Char('First Name', readonly=True)
    last_name = fields.Char('Last Name', readonly=True)
    name = fields.Char('Name', readonly=True)
    organization_id = fields.Char('Organization ID', readonly=True)
    title = fields.Char('Title', readonly=True)
    email = fields.Char('Email', readonly=True)
    email_status = fields.Char('Email Status', readonly=True)
    linkedin_url = fields.Char('LinkedIn', readonly=True)
    twitter_url = fields.Char('Twitter', readonly=True)
    github_url = fields.Char('Github', readonly=True)
    facebook_url = fields.Char('Facebook', readonly=True)
    photo_url = fields.Char('Photo', readonly=True)
    apl_people_company_id = fields.Many2one('apl.companies', string='Organization', readonly=True)
    country = fields.Char('Country', readonly=True)
    state = fields.Char('State', readonly=True)
    city = fields.Char('City', readonly=True)

    people_employment_history_ids = fields.One2many('apl.people.employment', 'apl_people_id', string="People")

    photo_image = fields.Binary("Photo", compute='_compute_image', store=True)

    status_converted = fields.Selection([
        ('lead', 'Lead'), ('contact', 'Contact')
    ])

    @api.depends('photo_url')
    def _compute_image(self):
        """ Function to load an image from URL or local file path """
        image = False
        for record in self:
            if record.photo_url:
                if record.photo_url.startswith(('http://', 'https://')):
                    # Load image from URL
                    try:
                        image = base64.b64encode(
                            requests.get(record.photo_url).content)
                    except Exception as e:
                        # Handle URL loading errors
                        raise UserError(_(f"Error loading image from URL: {str(e)}"))
                else:
                    # Load image from local file path
                    try:
                        with open(record.photo_url, 'rb') as image_file:
                            image = base64.b64encode(image_file.read())
                    except Exception as e:
                        # Handle local file loading errors
                        raise UserError(
                            _(f"Error loading image from local path: {str(e)}"))
            photo_image = image
            if photo_image:
                record.photo_image = photo_image

    def open_linkedin_profile(self):
        # Get the LinkedIn profile URL from a field in your model
        linkedin_profile_url = self.linkedin_url  # Replace with your field name
        if linkedin_profile_url:
            return {
                'type': 'ir.actions.act_url',
                'url': linkedin_profile_url,
                'target': 'new',
            }
    def open_twitter_profile(self):
        linkedin_profile_url = self.twitter_url  # Replace with your field name
        if linkedin_profile_url:
            return {
                'type': 'ir.actions.act_url',
                'url': linkedin_profile_url,
                'target': 'new',
            }
    def open_facebook_profile(self):
        # Get the LinkedIn profile URL from a field in your model
        linkedin_profile_url = self.facebook_url  # Replace with your field name
        if linkedin_profile_url:
            return {
                'type': 'ir.actions.act_url',
                'url': linkedin_profile_url,
                'target': 'new',
            }
    def open_github_profile(self):
        # Get the LinkedIn profile URL from a field in your model
        linkedin_profile_url = self.github_url  # Replace with your field name
        if linkedin_profile_url:
            return {
                'type': 'ir.actions.act_url',
                'url': linkedin_profile_url,
                'target': 'new',
            }

    def action_open_details(self):
        return {
            'name': 'People',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'apl.people',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
        
    def action_convert_contacts(self):
        ''' Open the apl.convert.data.wizard wizard to convert search results into Odoo contacts
        '''
        return {
            'name': _('Convert into Contacts'),
            'res_model': 'apl.convert.data.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'apl.people',
                'active_ids': self.ids,
                'op_name': 'contacts',
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }
    def action_convert_leads(self):
        ''' Open the apl.convert.data.wizard wizard to convert search results into Odoo leads
        '''
        return {
            'name': _('Convert into Leads'),
            'res_model': 'apl.convert.data.wizard',
            'view_mode': 'form',
            'context': {
                'active_model': 'apl.people',
                'active_ids': self.ids,
                'op_name': 'leads',
            },
            'target': 'new',
            'type': 'ir.actions.act_window',
        }

class ApolloPeopleEmployment(models.Model):
    _name = 'apl.people.employment'
    _description = 'Apollo People Employement History'

    apl_people_id = fields.Many2one('apl.people', string='People', readonly=True)
    degree = fields.Char('Degree', readonly=True)
    start_date = fields.Date('Start Date', readonly=True)
    end_date = fields.Date('End Date', readonly=True)
    grade_level = fields.Char('Grade Level', readonly=True)
    kind = fields.Char('Kind', readonly=True)
    major = fields.Char('Major', readonly=True)
    description = fields.Text('Description', readonly=True)
    