# -*- coding: utf-8 -*-
import base64
from odoo import api, fields, Command, models, _
from odoo.exceptions import UserError, AccessError
from odoo.tools import html_escape as escape

import requests
import json
import logging

_logger = logging.getLogger(__name__)


class ApolloComapniesResults(models.Model):
    _name = 'apl.companies'
    _description = 'Apollo Companies'

    apl_id = fields.Char('ID', readonly=True)
    name = fields.Char('Name', readonly=True)
    phone = fields.Char('Phone', readonly=True)
    email = fields.Char('Email', readonly=True)
    website_url = fields.Char('Website', readonly=True)
    blog_url = fields.Char('Blog', readonly=True)
    angellist_url = fields.Char('Angel List', readonly=True)
    linkedin_url = fields.Char('LinkedIn', readonly=True)
    linkedin_uid = fields.Char('LinkedIn UID', readonly=True)
    twitter_url = fields.Char('Twitter', readonly=True)
    facebook_url = fields.Char('Facebook', readonly=True)
    alexa_ranking = fields.Integer('Alexa Ranking', readonly=True)
    founded_year = fields.Integer('Founded Year', readonly=True)
    logo_url = fields.Char('Logo')
    primary_domain = fields.Char('Primary Domain', readonly=True)
    country = fields.Char('Country', readonly=True)
    state = fields.Char('State', readonly=True)
    city = fields.Char('City', readonly=True)

    apl_people_ids = fields.One2many('apl.people', 'apl_people_company_id', string="Peoples")

    logo_image = fields.Binary("Logo", compute='_compute_image', store=True)
    status_converted = fields.Selection([
        ('lead', 'Lead'), ('contact', 'Contact')
    ])

    @api.depends('logo_url')
    def _compute_image(self):
        """ Function to load an image from URL or local file path """
        image = False
        for record in self:
            if record.logo_url:
                if record.logo_url.startswith(('http://', 'https://')):
                    # Load image from URL
                    try:
                        image = base64.b64encode(
                            requests.get(record.logo_url).content)
                    except Exception as e:
                        # Handle URL loading errors
                        raise UserError(_(f"Error loading image from URL: {str(e)}"))
                else:
                    # Load image from local file path
                    try:
                        with open(record.logo_url, 'rb') as image_file:
                            image = base64.b64encode(image_file.read())
                    except Exception as e:
                        # Handle local file loading errors
                        raise UserError(
                            _(f"Error loading image from local path: {str(e)}"))
            logo_image = image
            if logo_image:
                record.logo_image = logo_image

    def action_open_people(self):
        people = self.mapped('apl_people_ids')
        action = self.env['ir.actions.actions']._for_xml_id('de_apollo_connector.action_apl_people')
        if len(people) > 1:
            action['domain'] = [('id', 'in', people.ids)]
        elif len(people) == 1:
            form_view = [(self.env.ref('de_apollo_connector.apl_people_form_view').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = people.id
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
