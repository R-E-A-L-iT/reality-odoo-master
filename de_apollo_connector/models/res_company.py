# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _

class Company(models.Model):
    _inherit = 'res.company'

    apl_instance_id = fields.Many2one('apl.instance', string="Instance")

    