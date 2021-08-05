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

class productType(models.Model):
    _inherit = "product.template"
    skuhidden = fields.One2many('ir.model.data', 'res_id', readonly=True)
    sku = fields.Char(related='skuhidden.name', string="SKU",  readonly=True)

class person(models.Model):
    _inherit = "res.partner"
    
    products = fields.One2many('stock.production.lot', 'owner', string="Products", readonly=True)
    parentProducts = fields.One2many(related='parent_id.products', string="Company Products", readonly=True)
    
class productInstance(models.Model):
    _inherit = "stock.production.lot"
    
    owner = fields.Many2one('res.partner', string="Owner")
    equipment_number = fields.Char(string="Equipment Number")
    sku = fields.Char(related='product_id.sku', readonly=True, string="SKU")
    expire = fields.Date(string='Expiration Date', default=lambda self: fields.Date.today(), required=False)
    formated_label = fields.Char(compute='_label')
    
    def _label(self):
        for i in self:
            r = i.formated_label =  i.name + " " + " " + i.product_id
            if(i.expire):
                r = r + " Expire: " str(i.expire)
            return