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

class order(models.Model):
    _inherit = 'sale.order'
    
    def _amount_all(self):
        raise UserError(_("NO!!"))

class proquotes(models.Model):
    _inherit = 'sale.order.line'
    
    selected = fields.Selection([
        ('true', "Yes"),
        ('false', "No")], default="true", required=True, help="Field to Mark Wether Customer as Selected Product")
    special = fields.Selection([
        ('multiple', "Multiple"),
        ('optional', "Optional")], default=False, help="Technical field for UX purpose.")
    optional = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default="no", required=True, help="Field to Mark Product as Optional")
    
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        raise UserError(_("No Update"))
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                if(line.selected == 'true'):
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })