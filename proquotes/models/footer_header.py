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


class footer_header(models.Model):
    _name = "header.footer"
    _description = "Hold info for Headers and Footer"
    _rec_name = 'name'
    name = fields.Char(string="Name", required=True)
    record_type = fields.Selection(
        [("Footer", "Footer"), ("Header", "Header")], required=True, default="Footer")
    url = fields.Char(string="Resourse URL", required=True)
    company_ids = fields.Many2many("res.company")
    active = fields.Boolean(string="Active", default=True)
    _order_by = 'active'

    def init_records(self, model):
        records = self.env[model]

        if ("footer_id" in dir(records) and "footer" in dir(records)):
            _logger.error("footer")

        if ("header_id" in dir(records) and "header" in dir(records)):
            _logger.error("header")
        _logger.warning(dir(records))
