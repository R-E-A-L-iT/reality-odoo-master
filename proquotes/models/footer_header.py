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
    _rec_name = "name"
    name = fields.Char(string="Name", required=True)
    record_type = fields.Selection(
        [("Footer", "Footer"), ("Header", "Header")], required=True, default="Footer"
    )
    url = fields.Char(string="Resourse URL", required=True)
    prefered = fields.Boolean(string="Prefered", default=False)
    company_ids = fields.Many2many("res.company")
    active = fields.Boolean(string="Active", default=True)
    _order_by = "active, prefered"

    def _get_footer(self, url):
        complete_url = "https://cdn.r-e-a-l.it/images/footer/" + url + ".png"
        footers = self.env["header.footer"].search(
            [("url", "=", complete_url), ("record_type", "=", "Footer")]
        )
        if len(footers) == 1:
            return footers[0].id
        elif len(footers) == 0:
            return self.env["header.footer"].create({"name": url, "url": complete_url})
        raise UserError("Invalid Match Count for URL: " + str(complete_url))

    def _get_header(self, url):
        complete_url = "https://cdn.r-e-a-l.it/images/header/" + url
        headers = self.env["header.footer"].search(
            [("url", "=", complete_url), ("record_type", "=", "Header")]
        )
        if len(headers) == 1:
            return headers[0].id
        elif len(headers) == 0:
            return self.env["header.footer"].create(
                {"name": url, "url": complete_url, "record_type": "Header"}
            )
        raise UserError("Invalid Match Count for URL: " + str(complete_url))

    def _init_footers(self, model):
        records = self.env[model].search([("footer", "!=", False)])
        for record in records:
            record.footer_id = self._get_footer(record.footer)

    def _init_headers(self, model):
        records = self.env[model].search([("header", "!=", False)])
        for record in records:
            record.header_id = self._get_header(record.header)

    def init_records(self, model):
        records = self.env[model]

        if "footer_id" in dir(records) and "footer" in dir(records):
            self._init_footers(model)
        if "header_id" in dir(records) and "header" in dir(records):
            self._init_headers(model)
