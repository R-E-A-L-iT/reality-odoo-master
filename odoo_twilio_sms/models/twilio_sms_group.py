# -*- coding: utf-8 -*-

from odoo import fields, models


class TwilioSmsGroup(models.Model):
    """SMS group for sending SMS to multiple person at once"""
    _name = 'twilio.sms.group'
    _description = 'Twilio SmS Group'

    name = fields.Char(string='Name', help='Name of the group', required=True)
    contact_ids = fields.One2many('res.partner',
                                  'twilio_contact_id',
                                  string='Partner Group', help='Members of '
                                                               'the group')
