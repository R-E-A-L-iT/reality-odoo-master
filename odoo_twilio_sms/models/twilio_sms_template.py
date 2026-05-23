# -*- coding: utf-8 -*-

from odoo import fields, models


class TwilioSmsTemplate(models.Model):
    """Model for holding SMS templates"""
    _name = 'twilio.sms.template'
    _description = 'Twilio SmS Template'

    name = fields.Char(string='Name', help='Name of Template', required=True)
    content = fields.Text(string='Content', help='Content of the Template')
