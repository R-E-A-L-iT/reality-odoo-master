# -*- coding: utf-8 -*-

import ast
import base64
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


class mail(models.TransientModel):
    _inherit = "mail.compose.message"

    def get_mail_values(self, res_ids):
        # Force 'reply_to' to be the same as 'email_from'
        result = super().get_mail_values(res_ids)
        for key in result:
            result[key]["reply_to"] = result[key]["email_from"]
            result[key]["reply_to_force_new"] = True
        return result




class MailMessage(models.Model):
    _inherit = 'mail.message'

    url = fields.Char(string="URL", compute="_get_page_url")

    def _get_page_url(self):
        for obj in self:
            if obj:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                discuss_url = f"/web#action=109&menu_id=86&active_id=discuss.channel_{obj.res_id}"
                obj.url = base_url + discuss_url
            else:
                obj.url = False

    @api.model_create_multi
    def create(self, values_list):
        messages = super(MailMessage, self).create(values_list)
        for message in messages:
            if message.message_type == 'comment':
                email_template = self.env.ref('proquotes.email_template_mail_message_notify', raise_if_not_found=False)
                # _logger.info("___ email_template: %s", email_template)
                if email_template:
                    mail_body = email_template.body_html
                    subject = email_template.subject
                    mail_body = mail_body.replace('author_name', message.author_id.name)
                    mail_body = mail_body.replace('discuss_url', message.url)
                    template_values = {
                        'subject': subject,
                        'email_from': message.author_id.email,
                        'email_to': message.reply_to,
                        'body_html': mail_body,
                    }
                    url = message.url
                    email_template.with_context(url=url).send_mail(message.id, email_values=template_values,
                                                                   force_send=True)
        return message
# class MailMessage(models.Model):
#     _inherit = 'mail.message'

    # @api.model_create_multi
    # def create(self, values_list):
    #     messages = super(MailMessage, self).create(values_list)
    #     for message in messages:
    #         if message.model=='sale.order' and message.res_id and message.body:
    #             order = self.env['sale.order'].sudo().browse(int(message.res_id))
    #             if order:
    #                 # Collect the recipients (partners)
    #                 # recipients = [(4, partner.id) for partner in message.partner_ids]
    #
    #                 # # Add email contacts from the order
    #                 # for contact in order.email_contacts:
    #                 #     recipients.append((4, contact.id))
    #
    #                 # # Add a static recipient
    #                 # sales_email = self.env['res.partner'].sudo().search([('email', '=', 'sales@r-e-a-l.it')], limit=1)
    #                 # if sales_email:
    #                 #     recipients.append((4, sales_email.id))
    #
    #                 # # Update the partner_ids with new recipients
    #                 # message.partner_ids = recipients
    #
    #                 base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #
    #                 # Append quotation info to the message body
    #                 body = message.body
    #                 lang = order.partner_id.lang
    #
    #                 # add back link tracker generated link
    #
    #
    #                 # if lang:
    #                 #     bottom_footer = _("\r\n \r\n Quotation: %s") % (str(base_url) + "/" + str(lang) + "/my/orders/" + str(order.id) + "?access_token=" + str(order.access_token))
    #                 #     body = body + bottom_footer # + str(message.partner_ids)
    #                 message.body = body
    #                 # message.notify = True
    #     return messages

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = [
            [
                'user',
                lambda pdata: pdata['type'] == 'user',
                {
                    'active': True,
                    'has_button_access': self._is_thread_message(msg_vals=msg_vals),
                }
            ], [
                'portal',
                lambda pdata: pdata['type'] == 'portal',
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'follower',
                lambda pdata: pdata['is_follower'],
                {
                    'active': False,  # activate only on demand if rights are enabled
                    'has_button_access': False,
                }
            ], [
                'customer',
                lambda pdata: True,
                {
                    'active': True,
                    'has_button_access': False,
                }
            ]
        ]
        if not self:
            return groups

        portal_enabled = isinstance(self, self.env.registry['portal.mixin'])
        if not portal_enabled:
            return groups

        customer = self._mail_get_partners(introspect_fields=False)[self.id]
        if customer:
            access_token = self._portal_ensure_token()
            local_msg_vals = dict(msg_vals or {})
            local_msg_vals['access_token'] = access_token
            local_msg_vals['pid'] = customer[0].id
            local_msg_vals['hash'] = self._sign_token(customer[0].id)
            local_msg_vals.update(customer[0].signup_get_auth_param()[customer[0].id])
            access_link = self._notify_get_action_link('view', **local_msg_vals)

            new_group = [
                ('portal_customer', lambda pdata: pdata['id'] == customer[0].id, {
                    'active': True,
                    'button_access': {
                        'url': access_link,
                    },
                    'has_button_access': True,
                })
            ]
        else:
            new_group = []

        # enable portal users that should have access through portal (if not access rights
        # will do their duty)
        portal_group = next(group for group in groups if group[0] == 'portal')
        portal_group[2]['active'] = True
        portal_group[2]['has_button_access'] = True

        return new_group + groups
