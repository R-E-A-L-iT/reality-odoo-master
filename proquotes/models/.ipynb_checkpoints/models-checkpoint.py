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
        raise UserError(_("NOW"))
        for values in vals_list:
            if values.get('display_type', self.default_get(['display_type'])['display_type']):
                values.update(product_id=False, price_unit=0, product_uom_qty=0, product_uom=False, customer_lead=0)

            values.update(self._prepare_add_missing_fields(values))
    
    def write(self, values):
        if(values.get('special') == 'multiple'):
            raise UserError(_("MULTIPLE"))
        else
            raise UserError(_("OTHER"))
        super().write(values);