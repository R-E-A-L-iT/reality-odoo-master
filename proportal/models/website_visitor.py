# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo import models, fields


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    ip_address = fields.Char(string="IP Address", help="The IP address of the visitor")
