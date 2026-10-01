# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    livechat_default_lead_user_id = fields.Many2one(
        'res.users',
        string='Default Lead Owner (Chatbot)',
        config_parameter='livechat_crm_enhanced.default_lead_user_id',
        help='Salesperson automatically assigned to leads created by the website chatbot. '
             'Leave empty to keep the chatbot operator as the owner.',
    )
    livechat_default_lead_team_id = fields.Many2one(
        'crm.team',
        string='Default Sales Team (Chatbot)',
        config_parameter='livechat_crm_enhanced.default_lead_team_id',
        help='Sales team automatically assigned to leads created by the website chatbot.',
    )
