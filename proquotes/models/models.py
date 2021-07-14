#-*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

class proquotes(models.Model):
    _inherit = 'sale.order.line'
    
    selected = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default="yes", required=True, help="Field to Mark Wether Customer as Selected Product")
    special = fields.Selection([
        ('multiple', "Multiple"),
        ('optional', "Optional")], default=False, help="Technical field for UX purpose.")
    optional = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default="no", required=True, help="Field to Mark Product as Optional")