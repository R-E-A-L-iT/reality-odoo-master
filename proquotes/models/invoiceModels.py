# -*- coding: utf-8 -*-

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


class InvoiceMain(models.Model):
    _inherit = "account.move"
    pricelist_id = fields.Many2one('product.pricelist', string="Pricelist")

    @api.onchange('pricelist_id')
    def _update_prices(self):
        pricelist = self.env['product.pricelist'].search(
            [('id', '=', self.pricelist_id.id)])
        if (len(pricelist) < 1):
            return
        pricelist = pricelist[-1]
        _logger.info(str(pricelist))
        for record in self.invoice_line_ids:
            product = record.product_id
            id = product.id
            priceResult = pricelist.item_ids.search(
                [('product_id', '=', id)])
            _logger.info(str(id))
            _logger.info("Search" + str(priceResult))
            # _logger.info(pricelist.item_ids)
        _logger.info("Prices Updated")


class invoiceLine(models.Model):
    _inherit = "account.move.line"

    applied_name = fields.Char(
        compute='get_applied_name', string="Applied Name")

    def get_applied_name(self):
        for record in self:
            id = self.env['ir.translation'].search([('value', '=', record.product_id.name),
                                                    ('name', '=', 'product.template,name')])
            if (len(id) > 1):
                id = id[-1]
            id = id.res_id
            name = self.env['ir.translation'].search([('res_id', '=', id),
                                                      ('name', '=',
                                                       'product.template,name'),
                                                      ('lang', '=', self.partner_id.lang)]).value
            if (name == False or name == ""):
                name = record.product_id.name
            record.applied_name = name
