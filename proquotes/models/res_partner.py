# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo import models, fields


class person(models.Model):
    _inherit = "res.partner"

    products = fields.One2many("stock.lot", "owner", string="Products")
