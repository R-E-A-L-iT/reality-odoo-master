# -*- coding: utf-8 -*-


import logging

from odoo import fields, models
from odoo import models, fields

_logger = logging.getLogger(__name__)

class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"
    
    selected = fields.Selection([
        ('true', "Yes"),
        ('false', "No")], default="true", required=True, help="Field to Mark Wether Customer has Selected Product")
    
    sectionSelected = fields.Selection([
        ('true', "Yes"),
        ('false', "No")], default="true", required=True, help="Field to Mark Wether Container Section is Selected")
    
    special = fields.Selection([
        ('regular', "regular"),
        ('multiple', "Multiple"),
        ('optional', "Optional")], default='regular', required=True, help="Technical field for UX purpose.")
    
    hiddenSection = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default='no', required=True, help="Field To Track if Sections are folded")
    
    optional = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default="no", required=True, help="Field to Mark Product as Optional")
    
    quantityLocked = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], string="Lock Quantity", default="yes", required=True, help="Field to Lock Quantity on Products")

    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
        help='Default percentage discount to apply when this template is used.'
    )