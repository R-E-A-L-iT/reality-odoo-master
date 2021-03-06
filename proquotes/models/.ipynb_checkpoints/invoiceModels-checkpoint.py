#-*- coding: utf-8 -*-

import ast
import base64
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

class invoiceLine(models.Model):
    _inherit = "account.move.line"
    
    applied_name = fields.Char(compute='get_applied_name', string="Applied Name")
    
    def get_applied_name(self):
        for record in self:
            id = self.env['ir.translation'].search([('value', '=', record.product_id.name),
                                                   ('name', '=', 'product.template,name')])
            if(len(id) > 1):
                id = id[-1]
            id = id.res_id
            name = self.env['ir.translation'].search([('res_id', '=', id),
                                                      ('name', '=', 'product.template,name'),
                                                      ('lang', '=', self.partner_id.lang)]).value
            if(name == False or name  == ""):
                name = record.product_id.name
            record.applied_name = name