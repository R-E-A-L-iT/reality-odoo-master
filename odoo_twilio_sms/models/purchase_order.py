# -*- coding: utf-8 -*-

from odoo import models, _


class PurchaseOrder(models.Model):
    """Inheriting purchase order for including Twilio functions"""
    _inherit = 'purchase.order'

    def action_purchase_twilio_sms(self):
        """Action for opening SMS wizard view"""
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
