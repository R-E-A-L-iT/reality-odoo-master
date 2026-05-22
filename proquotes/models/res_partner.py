# -*- coding: utf-8 -*-


import logging

from odoo import fields, models
from odoo import models, fields

_logger = logging.getLogger(__name__)

class person(models.Model):
    _inherit = "res.partner"

    products = fields.One2many("stock.lot", "owner", string="Products")