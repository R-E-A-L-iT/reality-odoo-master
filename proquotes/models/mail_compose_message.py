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

        model = self.env.context.get('default_model')
        res_id = self.env.context.get('default_res_id') or self.env.context.get('active_id')
        template_model = self.env['mail.compose.message']

        if model in ['sale.order']:
            defaults['partner_ids'] = [(5, 0, 0)]

            order = self.env['sale.order'].browse(res_id)
            
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