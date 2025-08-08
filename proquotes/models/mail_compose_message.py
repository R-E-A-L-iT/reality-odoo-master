# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'
    
    template_id = fields.Many2one(
        'mail.template',
        string='Use Template',
        # domain=lambda self: [('name', 'in', ['General Sales', 'Rental', 'Renewal'])]
    )

    # this clears the default recipients that are autofilled into the wizard. this is here because we don't want to send emails to the email address attatched to the company contact.
    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)
        res_id_target = None 
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
        res_id = self.env.context.get('default_res_id') or self.env.context.get('active_id')
        template_model = self.env['mail.compose.message']

        if model in ['sale.order']:
            defaults['partner_ids'] = [(5, 0, 0)]

            order = self.env['sale.order'].browse(res_id_target)
            
            if order:
                _logger.info("Order found: " + order.name)

            if order.website_id:
                template = self.env['mail.template'].search([
                    ('name', '=', 'eCommerce Quote Send')
                ], limit=1)

                if template:
                    defaults['template_id'] = template.id
                    _logger.info("Applied eCommerce Quote Send template")
            else:
                template = self.env['mail.template'].search([
                    ('name', '=', 'General Sales')
                ], limit=1)
                
                if template:
                    defaults['template_id'] = template.id
                    _logger.info("Applied General Sales template")
                    # defaults['use_template'] = True


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
                # defaults['use_template'] = True
                defaults['attachment_ids'] = [(5, 0, 0)]

        return defaults

    def _prepare_mail_values_dynamic(self, res_ids):
        """
        Override to add dynamic user_id parameter to quotation URLs
        for each recipient when sending sale order emails.
        """
        mail_values_all = super()._prepare_mail_values_dynamic(res_ids)
        
        # Only process if we're dealing with sale.order model
        if self.model != 'sale.order':
            return mail_values_all
            
        # Process each record individually to customize URLs per recipient
        for res_id in res_ids:
            if res_id not in mail_values_all:
                continue
                
            mail_values = mail_values_all[res_id]
            
            # Get the recipient partner_ids for this specific email
            recipient_ids = mail_values.get('recipient_ids', [])
            if not recipient_ids:
                continue
                
            # If there are multiple recipients, we need to send individual emails
            # This ensures each recipient gets their own user_id in the URL
            if len(recipient_ids) > 1:
                # For multiple recipients, we'll handle this in _send_mail_recipients
                # by creating separate emails for each recipient
                continue
                
            # For single recipient, modify the URL directly
            recipient_id = recipient_ids[0][1] if recipient_ids and len(recipient_ids[0]) > 1 else None
            if recipient_id:
                partner = self.env['res.partner'].browse(recipient_id)
                if partner.exists():
                    # Modify the body to include user_id in quotation URLs
                    body = mail_values.get('body', '')
                    if body:
                        modified_body = self._add_user_id_to_quotation_urls(body, partner.id)
                        mail_values['body'] = modified_body
                        mail_values['body_html'] = modified_body
        
        return mail_values_all

    def _add_user_id_to_quotation_urls(self, body, user_id):
        """
        Add user_id parameter to quotation URLs in the email body.
        Works with the custom controller at /check_quotation_redirect/<int:order_id>/<string:access_token>
        
        :param body: The email body content
        :param user_id: The recipient's partner ID
        :return: Modified body with user_id added to quotation URLs
        """
        if not body or not user_id:
            return body
            
        # Pattern to match the custom quotation redirect URLs from proquotes module
        url_pattern = r'(/check_quotation_redirect/\d+/[a-zA-Z0-9]+)'
        
        def add_user_id_param(match):
            url = match.group(1)
            separator = '&' if '?' in url else '?'
            return f"{url}{separator}user_id={user_id}"
        
        # Replace all matching URLs with user_id parameter
        modified_body = re.sub(url_pattern, add_user_id_param, body)
        
        return modified_body

    def _send_mail_recipients(self, mail_values_all, **kwargs):
        """
        Override to handle multiple recipients by sending individual emails
        when dealing with sale orders to ensure each gets their own user_id.
        
        This works with the custom sale.order model in proquotes that uses
        _notify_get_recipients_groups to generate the button URLs.
        """
        if self.model != 'sale.order':
            return super()._send_mail_recipients(mail_values_all, **kwargs)
            
        # For sale orders with multiple recipients, send individual emails
        individual_mails = {}
        
        for res_id, mail_values in mail_values_all.items():
            recipient_ids = mail_values.get('recipient_ids', [])
            
            if len(recipient_ids) <= 1:
                # Single or no recipient, process normally but still add user_id
                if len(recipient_ids) == 1:
                    recipient_id = recipient_ids[0][1] if len(recipient_ids[0]) > 1 else None
                    if recipient_id:
                        partner = self.env['res.partner'].browse(recipient_id)
                        if partner.exists():
                            body = mail_values.get('body', '')
                            if body:
                                modified_body = self._add_user_id_to_quotation_urls(body, partner.id)
                                mail_values['body'] = modified_body
                                mail_values['body_html'] = modified_body
                
                individual_mails[res_id] = mail_values
                continue
                
            # Multiple recipients - create individual mail for each
            base_values = mail_values.copy()
            
            for recipient_tuple in recipient_ids:
                if len(recipient_tuple) < 2:
                    continue
                    
                recipient_id = recipient_tuple[1]
                partner = self.env['res.partner'].browse(recipient_id)
                
                if not partner.exists():
                    continue
                
                # Create individual mail values for this recipient
                individual_mail_values = base_values.copy()
                individual_mail_values['recipient_ids'] = [recipient_tuple]
                
                # Modify URLs for this specific recipient
                body = individual_mail_values.get('body', '')
                if body:
                    modified_body = self._add_user_id_to_quotation_urls(body, partner.id)
                    individual_mail_values['body'] = modified_body
                    individual_mail_values['body_html'] = modified_body
                
                # Create unique key for each recipient email
                unique_key = f"{res_id}_{recipient_id}"
                individual_mails[unique_key] = individual_mail_values
        
        # Send the individualized emails
        return super()._send_mail_recipients(individual_mails, **kwargs)