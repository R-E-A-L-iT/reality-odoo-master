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

    # this clears the default recipients that are autofilled into the wizard. this is here because we don't want to send emails to the email address attatched to the company contact.
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        model = self.env.context.get('default_model')
        template_model = self.env['mail.compose.message']

        res_id = self.env.context.get('default_res_id')
        check_needed = self.env.context.get('check_invoice_recipients')

        if check_needed and model == 'account.move' and res_id:
            move = self.env[model].browse(res_id)

            # Get follower emails
            valid_followers = move.message_partner_ids.filtered(
                lambda p: p.email and not p.email.lower().endswith('@r-e-a-l.it')
                          and not p.user_ids  # not internal user
            )

            if not valid_followers:
                warning = ("⚠️ Warning: This invoice will only be sent to internal addresses "
                           "like yourself or 'sales@r-e-a-l.it'. Make sure to add individual recipients.")
                defaults['warning_message'] = warning

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