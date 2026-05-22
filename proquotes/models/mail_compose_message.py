# -*- coding: utf-8 -*-

import ast

import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    template_id = fields.Many2one(
        'mail.template',
        string='Use Template',
    )

    # this clears the default recipients that are autofilled into the wizard. this is here because we don't want to send emails to the email address attatched to the company contact.
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        res_id_target = None
        company = self.env.company
        ba_email = company.ba_email_template_id
        _logger.info(">>>>>>>>>>>>>37>>>>ba_email %s %s %s",ba_email,self.env.user.company_id,self.env.user)
        if 'res_ids' in defaults and defaults['res_ids']:
            try:
                parsed_res_ids = ast.literal_eval(defaults['res_ids'])
                
                if isinstance(parsed_res_ids, list) and parsed_res_ids:
                    res_id_target = parsed_res_ids[0]
                elif isinstance(parsed_res_ids, int):
                    res_id_target = parsed_res_ids
                else:
                    _logger.warning("defaults['res_ids'] contained unhandled format: %s", defaults['res_ids'])
            except (ValueError, SyntaxError) as e:
                _logger.error("Failed to parse defaults['res_ids'] string '%s': %s", defaults['res_ids'], e)

        model = self.env.context.get('default_model')
        template_model = self.env['mail.compose.message']

        if model in ['sale.order']:
            defaults['partner_ids'] = [(5, 0, 0)]

            order = self.env['sale.order'].browse(res_id_target)
            
            if order:
                _logger.info("Order found: " + order.name)

            if order.website_id:
                if ba_email:
                    defaults['template_id'] = ba_email.id
                    _logger.info("Applied eCommerce Quote Send template")

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