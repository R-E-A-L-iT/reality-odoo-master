# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ResPartner(models.Model):
    """Inheriting res partner for including Twilio fields and functions"""
    _inherit = 'res.partner'

    twilio_contact_id = fields.Many2one('twilio.sms.group',
                                        string='Twilio ID',
                                        help='Twilio Connection ID')

    def action_partner_twilio_sms(self):
        """Action for opening the SMS wizard view"""
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Message Content'),
            'res_model': 'sms.builder',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.id},
            'views': [[False, 'form']]
        }
        return action
