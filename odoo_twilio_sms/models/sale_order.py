# -*- coding: utf-8 -*-

from odoo import models, _


class SaleOrder(models.Model):
    """Inheriting sale order for adding Twilio functions"""
    _inherit = 'sale.order'

    def action_twilio_sms(self):
        """Action for opening Twilio SMS wizard view"""
        action = {
            'type': 'ir.actions.act_window',
            'name': _('Message Content'),
            'res_model': 'sms.builder',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_partner_id': self.partner_id.id},
            'views': [[False, 'form']]
        }
        return action
