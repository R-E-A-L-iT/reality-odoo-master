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


class renewal_map(models.Model):
    _name = 'renewal.map'
    _description = 'Map Product Types to Renewal Offers'
    _rec_name = "product_id"
    product_id = fields.Many2one(
        'product.product', string="Product", required=True)
    product_offers = fields.One2many(
        comodel_name='renewal.entry',  inverse_name="map_id", string="Renewal Offers")

# Ensure that that there is only one map per product
    @api.onchange('product_id')
    def verify_unique(self):
        if (len(self.product_id) == 0):
            return
        records = self.env['renewal.map'].search(
            [('product_id', '=', self.product_id.id)])
        if (len(records) > 1):
            raise ValidationError(
                "Renewal Map Entry Already Made for: " + str(self.product_id.name))
        if (len(records) == 1 and records[0].id != self.id):
            raise ValidationError(
                "Renewal Map Entry Already Made for: " + str(self.product_id.name))


class renewal_entry(models.Model):
    _name = 'renewal.entry'
    _description = 'Hold order information for renewal.map'
    _rec_name = 'product_id'
    _order = 'order'
    order = fields.Integer(string="Order", required=True)
    product_id = fields.Many2one(
        'product.product', string="Product", required="True")
    map_id = fields.Many2one(comodel_name='renewal.map')
