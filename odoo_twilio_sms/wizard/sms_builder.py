# -*- coding: utf-8 -*-

from odoo import fields, models, _
from twilio.rest import Client
from twilio.base.exceptions import TwilioException


class SmsBuilder(models.TransientModel):
    """Class to handle all the functions required in send sms """
    _name = 'sms.builder'
    _description = 'SMS Builder'

    partner_id = fields.Many2one('res.partner', string='Recipient',
                                 help='Receiving User')
    receiving_number = fields.Char(string='Receiving Number',
                                   help='Receiving Number',
                                   required=True, readonly=False,
                                   related='partner_id.mobile')
    template_id = fields.Many2one('twilio.sms.template',
                                  string='Select Template',
                                  help='Message Template')
    text_message = fields.Text(string='Message', help='Message Content',
                               required=True, related='template_id.content',
                               readonly=False)
    account_id = fields.Many2one('twilio.account',
                                 string='Twilio Account', help='Choose the '
                                                               'Twilio '
                                                               'account',
                                 required=True)

    def action_confirm_sms(self):
        """Send sms to the corresponding user by using the twilio connection"""
        try:
            client = Client(self.account_id.account_sid,
                            self.account_id.auth_token)
            message = client.messages.create(
                body=self.text_message,
                from_=self.account_id.from_number,
                to=self.receiving_number
            )
            if message.sid:
                message_data = _("Message Sent!")
                type_data = 'success'
            else:
                message_data = _("Message Not Sent!")
                type_data = 'warning'
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message_data,
                    'type': type_data,
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }
        except TwilioException:
            message_data = _("Message Not Sent!")
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'message': message_data,
                    'type': 'warning',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_window_close'
                    },
                }
            }
