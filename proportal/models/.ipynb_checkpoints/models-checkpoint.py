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
    _inherit = "product.product"
    skuhidden = fields.One2many('ir.model.data', 'res_id', readonly=True)
    sku = self.sku.name

class person(models.Model):
    _inherit = "res.partner"
    
    products = fields.One2many('stock.production.lot', 'owner', string="Products")
    
class productInstance(models.Model):
    _inherit = "stock.production.lot"
    
    owner = fields.Many2one('res.partner', string="Owner")
    sku = fields.Char(compute='getSKU', readonly=True)
    expire = fields.Date(string='Expiration Date', default=lambda self: fields.Date.today(), required=False)
    
    def getSKU(self):
        raise UserError(_("Not Ready Yet"))
        #product = self.get('product_id')
        #data = self.env['ir.model.data']
        #raise UserError(_(str(data.search([('module', '=', 'product.product'), ('res_id','=', product)]))))
        #for x in self:
        #    if x.external_id:
        #        x.sku = x.external_id
        #   else:
        #       x.sku=""