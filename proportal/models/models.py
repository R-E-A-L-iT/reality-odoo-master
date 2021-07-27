#-*- coding: utf-8 -*-

import ast
import base64
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

class person(models.Model):
    _inherit = "res.partner"
    
    products = fields.One2many('stock.production.lot', 'owner', string="Products")
    
class productInstance(models.Model):
    _inherit = "stock.production.lot"
    
    owner = fields.Many2one('res.partner', string="Owner")
    sku = fields.Char(compute='getSKU')
    expire = fields.Date(string='Expiration Date', default=lambda self: fields.Date.today(), required=False)
    
    def getSKU(self):
        for x in self:
            x.sku = "No SKU"