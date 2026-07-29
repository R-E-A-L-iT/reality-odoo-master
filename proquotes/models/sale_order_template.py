# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
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

class SaleOrderTemplate(models.Model):
    _inherit = 'sale.order.template'

    header_id = fields.Many2one(
        'quotation.document',
        string="Default Preview Header",
        domain="[('active', '=', True), ('doc_class', '=', 'preview'), ('document_type', '=', 'header')]",
    )

    def _prepare_sale_order_line_values(self, order, line, **kwargs):
        vals = super()._prepare_sale_order_line_values(order, line, **kwargs)
        if hasattr(line, 'discount') and line.discount:
            vals['discount'] = line.discount
        if getattr(line, 'section_name_translations', False):
            vals['section_name_translations'] = line.section_name_translations
        return vals

    def _prepare_sale_order_optional_line_values(self, order, option_line, **kwargs):
        vals = super()._prepare_sale_order_optional_line_values(order, option_line, **kwargs)
        if hasattr(option_line, 'discount') and option_line.discount:
            vals['discount'] = option_line.discount
        if getattr(option_line, 'section_name_translations', False):
            vals['section_name_translations'] = option_line.section_name_translations
        return vals