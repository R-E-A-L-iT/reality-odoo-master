# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from twilio.rest import Client
from twilio.base.exceptions import TwilioException


class TwilioSms(models.Model):
    """Can send sms, select the receiver and template or content,
    then can send the sms"""
    _name = 'twilio.sms'
    _description = 'Twilio SMS'

    name = fields.Char(string='Name', help='Name of Twilio SMS', required=True)
    partner_id = fields.Many2one('twilio.sms.group',
                                 string='Receiving Group',
                                 help='Select the receiving groups',
                                 required=True)
    template_body_id = fields.Many2one('twilio.sms.template',
                                       string='SMS Template',
                                       help='Select the message template')
    content = fields.Text(string='Content', help='SMS Content', required=True,
                          related='template_body_id.content', readonly=False)
    scheduled_date = fields.Date(string='Scheduled Date', help='Scheduled '
                                                               'Date for '
                                                               'sending SMS',
                                 default=fields.Date.today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('sent', 'Sent'),
    ], default='draft', string='State', help='State of SMS')
    account_id = fields.Many2one('twilio.account',
                                 string='Twilio Account', help='Choose the '
                                                               'Twilio '
                                                               'account',
                                 required=True)

    def action_confirm_sms(self):
        """Send SMS when click the action button"""
        for val in self:
            val.state = 'confirm'
            if val.scheduled_date == fields.Date.today():
                self.send_sms(val)

    def send_sms_on_time(self):
        """Send SMS when schedule the time"""
        for val in self.env['twilio.sms'].search([]):
            if (val.state == 'confirm' and val.scheduled_date ==
                    fields.date.today()):
                self.send_sms(val)

    @api.model
    def send_sms(self, val):
        """Send SMS to all users"""
        count = len(val.partner_id.contact_ids)
        for partner in val.partner_id.contact_ids:
            try:
                client = Client(val.account_id.account_sid,
                                val.account_id.auth_token)
                message = client.messages.create(
                    body=val.content,
                    from_=val.account_id.from_number,
                    to=partner.phone
                )
                if message.sid:
                    count = count - 1
                if not count:
                    val.state = 'sent'
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': 'Message Sent Successfully',
                            'type': 'success',
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
