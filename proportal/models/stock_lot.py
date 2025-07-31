# -*- coding: utf-8 -*-

import ast
import base64
import requests
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class productInstance(models.Model):
    _inherit = "stock.lot"

    # Store Data For CCP Tracking
    owner = fields.Many2one("res.partner", string="Owner")
    equipment_number = fields.Char(string="Equipment Number")
    sku = fields.Char(related="product_id.sku", readonly=True, string="SKU")
    expire = fields.Date(
        string="Expiration Date",
        default=lambda self: fields.Date.today(),
        required=False,
    )
    formated_label = fields.Char(compute="_label")
    publish = fields.Boolean(string="publish", default="True")

    firmware_version = fields.Text(string='Firmware Version', help='Firmware version associated with this lot.')

    # Automate formated_label
    def _label(self):
        for i in self:
            parsedLabel = i.product_id.name.split(" - ")
            if len(parsedLabel) > 1:
                result = parsedLabel[1]
                for section in parsedLabel[2:]:
                    result = result + " - " + str(section)
                parsedLabel = result
            else:
                parsedLabel = parsedLabel[0]
            r = "#ccplabel+" + str(i.name) + "+" + str(parsedLabel)
            if i.expire != False:
                r = r + "+" + str(i.expire) 
            i.formated_label = r
