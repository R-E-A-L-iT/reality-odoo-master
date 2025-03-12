# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    apl_auto_contacts = fields.Boolean(
        string='Auto update contacts', config_parameter='apl.contacts.auto')
    apl_auto_leads = fields.Boolean(
        string='Auto update leads', config_parameter='apl.leads.auto')
        
    apl_instance_id = fields.Many2one(comodel_name="apl.instance", related='company_id.apl_instance_id',readonly=False,)