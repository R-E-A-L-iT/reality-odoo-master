# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ba_email_template_id = fields.Many2one('mail.template', string="Email Template", related='company_id.ba_email_template_id', readonly=False)
