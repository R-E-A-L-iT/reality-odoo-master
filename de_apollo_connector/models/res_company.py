# -*- coding: utf-8 -*-

from odoo import models, fields


class Company(models.Model):
    _inherit = 'res.company'

    apl_instance_id = fields.Many2one('apl.instance', string="Instance")
