# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class SaleOrderTemplateLine(models.Model):
    _inherit = "sale.order.template.line"
    
    # Per-language section titles carried by the template so quotes created from
    # it preserve the correct translations. See sale.order.line.section_name_translations.
    section_name_translations = fields.Json(string="Section Name Translations")

    hiddenSection = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default='no', required=True, help="Field To Track if Sections are folded")

    quantityLocked = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], string="Lock Quantity", default="yes", required=True, help="Field to Lock Quantity on Products")

    discount = fields.Float(
        string='Discount (%)',
        digits='Discount',
        default=0.0,
        help='Default percentage discount to apply when this template is used.'
    )