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
            r = i.name + " " + " " + i.product_id.name
            if(i.expire != False):
                r = r + " Expiration: " + str(i.expire)
            i.formated_label = r
            return

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def init(self):
        portal_purchase_order_user_rule = self.env.ref('purchase.portal_purchase_order_user_rule')
        if portal_purchase_order_user_rule:
            portal_purchase_order_user_rule.sudo().write({
                'domain_force': "['|', ('message_partner_ids','child_of',[user.partner_id.id]),('partner_id', 'child_of', [user.partner_id.id])]"
            })
        portal_purchase_order_line_rule = self.env.ref('purchase.portal_purchase_order_line_rule')
        if portal_purchase_order_line_rule:
            portal_purchase_order_line_rule.sudo().write({
                'domain_force': "['|',('order_id.message_partner_ids','child_of',[user.partner_id.id]),('order_id.partner_id','child_of',[user.partner_id.id])]"
            })