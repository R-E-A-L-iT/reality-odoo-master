# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.tools import float_round
from odoo.exceptions import UserError
import requests

class ResCompany(models.Model):
    _inherit = "res.company"

    ba_email_template_id = fields.Many2one('mail.template', string="Email Template")

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ba_email_template_id = fields.Many2one('mail.template', string="Email Template", related='company_id.ba_email_template_id', readonly=False)
