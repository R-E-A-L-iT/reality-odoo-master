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
    special = fields.Selection([
        ('multiple', "Multiple"),
        ('optional', "Optional")], default=False, help="Technical field for UX purpose.")
    
    def create(self, vals_list):
        for values in vals_list:
            if not values.get('special', self.default_get(['special'])['special']):
                raise UserError(_('Evidence of Sucsess'))
        lines = super().create(vals_list)
    