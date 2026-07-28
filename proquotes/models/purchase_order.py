# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re
from math import ceil

from datetime import date, datetime, timedelta
import functools
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression as exp
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
from odoo.models import BaseModel as BSM
from collections import defaultdict
from odoo.http import request
from odoo.http import Response as Responseht
from odoo.http import FutureResponse as FutureResponseht

# Odoo 19 trimmed odoo.tools; import only what this module uses.
from odoo.tools import get_lang
import werkzeug.datastructures
import werkzeug.exceptions
import werkzeug.local
import werkzeug.routing
import werkzeug.security
import werkzeug.wrappers
import werkzeug.wsgi
from werkzeug.urls import URL, url_parse, url_encode, url_quote
from werkzeug.exceptions import (HTTPException, BadRequest, Forbidden,
                                 NotFound, InternalServerError)
try:
    from werkzeug.middleware.proxy_fix import ProxyFix as ProxyFix_
    ProxyFix = functools.partial(ProxyFix_, x_for=1, x_proto=1, x_host=1)
except ImportError:
    from werkzeug.contrib.fixers import ProxyFix
try:
    from werkzeug.utils import send_file as _send_file
except ImportError:
    from .tools._vendor.send_file import send_file as _send_file

class purchase_order(models.Model):
    _inherit = "purchase.order"

    date_approve = fields.Datetime(
        string="Confirmation Date",
        copy=False,
        tracking=True,
        readonly=False,
    )

    def _get_available_footer_domain(self):
        return [
            ("active", "=", True),
            ("doc_class", "=", "preview"), ("document_type", "=", "footer"),
        ]

    @api.model
    def _get_first_available_footer(self, company=False):
        domain = self._get_available_footer_domain()
        footers = self.env["quotation.document"].search(domain, order="id asc")
        if company:
            company_specific = footers.filtered(
                lambda f: not f.company_ids or company in f.company_ids
            )
            if company_specific:
                return company_specific[0]
        return footers[:1]

    @api.model
    def _get_user_company_footer(self, user=False, company=False):
        user = user or self.env.user
        company = company or self.env.company

        if not user or not company:
            return self.env["quotation.document"]

        line = self.env["res.users.company.footer"].search(
            [
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if line and line.footer_id and line.footer_id.active and line.footer_id.document_type == "footer":
            return line.footer_id

        return self.env["quotation.document"]

    @api.model
    def _get_company_default_footer(self, company=False):
        company = company or self.env.company
        if (
            company
            and company.default_footer_id
            and company.default_footer_id.active
            and company.default_footer_id.document_type == "footer"
        ):
            return company.default_footer_id
        return self.env["quotation.document"]

    @api.model
    def _default_footer_id(self):
        user = self.env.user
        company = self.env.company

        footer = self._get_user_company_footer(user=user, company=company)
        if footer:
            return footer.id

        footer = self._get_company_default_footer(company=company)
        if footer:
            return footer.id

        footer = self._get_first_available_footer(company=company)
        return footer.id if footer else False

    footer_id = fields.Many2one(
        "quotation.document",
        string="Footer",
        required=True,
        domain="[('active', '=', True), ('doc_class', '=', 'preview'), ('document_type', '=', 'footer')]",
        default=_default_footer_id,
    )

    @api.onchange("user_id", "company_id")
    def _onchange_user_or_company_set_footer(self):
        for order in self:
            company = order.company_id or self.env.company
            user = order.user_id or self.env.user

            footer = order._get_user_company_footer(user=user, company=company)
            if not footer:
                footer = order._get_company_default_footer(company=company)
            if not footer:
                footer = order._get_first_available_footer(company=company)

            order.footer_id = footer.id if footer else False

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        user_id = defaults.get("user_id") or self.env.uid
        company_id = defaults.get("company_id") or self.env.company.id

        user = self.env["res.users"].browse(user_id)
        company = self.env["res.company"].browse(company_id)

        footer = self._get_user_company_footer(user=user, company=company)
        if not footer:
            footer = self._get_company_default_footer(company=company)
        if not footer:
            footer = self._get_first_available_footer(company=company)

        if footer:
            defaults["footer_id"] = footer.id

        return defaults