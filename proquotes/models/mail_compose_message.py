# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    template_id = fields.Many2one(
        'mail.template',
        string='Use Template',
        domain=lambda self: [('name', 'in', ['General Sales', 'Rental', 'Renewal'])]
    )

    # this overrides the check that prevents emails from being sent if the partner_id has no email set
    def _get_invalid_recipients(self):
        return []

    # this clears the default recipients that are autofilled into the wizard. this is here because we don't want to send emails to the email address attatched to the company contact.
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        model = self.env.context.get('default_model')
        template_model = self.env['mail.compose.message']

        if model in ['sale.order']:
            defaults['partner_ids'] = [(5, 0, 0)]

            template = self.env['mail.template'].search([
                ('name', '=', 'General Sales')
            ], limit=1)
            
            if template:
                defaults['template_id'] = template.id

        elif model in ['account.move']:
            if 'partner_ids' in template_model._fields:
                defaults['partner_ids'] = [(5, 0, 0)]

                template = self.env['mail.template'].search([
                    ('name', '=', 'Invoice Payment Thank You')
                ], limit=1)

            if 'mail_partner_ids' in template_model._fields:
                defaults['mail_partner_ids'] = [(5, 0, 0)]
                
                template = self.env['mail.template'].search([
                    ('name', '=', 'Invoice: Send by email')
                ], limit=1)

            if template:
                defaults['template_id'] = template.id
                defaults['attachment_ids'] = [(5, 0, 0)]

        return defaults