# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def prepare_google_message(self):
        """
        Prepare lead for Google message by setting simple_email_layout to True
        and returning the original value for restoration.
        """
        original_value = self.simple_email_layout
        
        if not self.simple_email_layout:
            self.write({'simple_email_layout': True})
        
        return {'original_value': original_value}

    def restore_google_message_settings(self, original_value):
        """
        Restore the original simple_email_layout value after sending.
        """
        if self.simple_email_layout != original_value:
            self.write({'simple_email_layout': original_value})


# class ResUsers(models.Model):
#     _inherit = 'res.users'

#     ba_mass_signature = fields.Html(string='Mass Signature')
