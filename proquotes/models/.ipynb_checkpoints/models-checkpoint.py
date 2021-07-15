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
            
    def _amount_by_group(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.order_line:
                if(line.selected == 'true'):
                    price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                    taxes = line.tax_id.compute_all(price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
                    for tax in line.tax_id:
                        group = tax.tax_group_id
                        res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                        for t in taxes:
                            if t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids:
                                res[group]['amount'] += t['amount']
                                res[group]['base'] += t['base']
                res = sorted(res.items(), key=lambda l: l[0].sequence)
                order.amount_by_group = [(
                    l[0].name, l[1]['amount'], l[1]['base'],
                    fmt(l[1]['amount']), fmt(l[1]['base']),
                    len(res),
                ) for l in res]

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