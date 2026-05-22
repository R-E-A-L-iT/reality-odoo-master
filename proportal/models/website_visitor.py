# -*- coding: utf-8 -*-



from odoo import fields, models
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    ip_address = fields.Char(string="IP Address", help="The IP address of the visitor")