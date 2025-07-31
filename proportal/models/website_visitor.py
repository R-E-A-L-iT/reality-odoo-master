import logging
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    ip_address = fields.Char(string="IP Address", help="The IP address of the visitor")