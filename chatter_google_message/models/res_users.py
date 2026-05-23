# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    ba_mass_signature = fields.Html(string='Mass Signature')
