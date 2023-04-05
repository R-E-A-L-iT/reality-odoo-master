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
        comodel_name='renewal.entry', string="Renewal Offers")


class renewal_entry(models.Model):
    _name = 'renewal.entry'
    _description = 'Hold order information for renewal.map'
    order = fields.Integer(string="Order", required=True)
    product_id = fields.Many2one(
        'product.product', string="Product", required="True")
    map_id = fields.Many2One(comodel_name='renewal.map',
                             inverse_name='product_offers')
