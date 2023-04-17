# -*- coding: utf-8 -*-

import ast
import base64
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class company(models.Model):
    _inherit = "res.partner"

    def _calc_nick(self):
        if (self.is_company == True):
            self.company_nickname = False
        else:
            self.company_nickname = "_"

    def init_company_nickname(self):
        _logger.error("INIT NICKNAME")
        for partner in self.env['res.partner'].search([('company_nickname', '=', False)]):
            partner.company_nickname = "_"

        for partner in self.env['res.partner'].search([('company_nickname', '=', False), ('active', '=', False)]):
            partner.company_nickname = "_"

    company_nickname = fields.Char(
        string="Unique Company Nickname", required=True)

    @api.onchange("is_company")
    def type_change(self):
        if (self.is_company == True and self.company_nickname == "_"):
            self.company_nickname = False
        elif (self.is_company == False and self.company_nickname == False):
            self.company_nickname = "_"

    @api.onchange("company_nickname")
    def verify_unique(self):
        if (self.company_nickname == False):
            return
        if (self.is_company == True and self.company_nickname == "_"):
            raise UserError("Company Nickname Cannot Be _")
        records = self.env['renewal.map'].search(
            [('company_nickname', '=', self.company_nickname)])
        if (len(records) > 1):
            raise ValidationError(
                "Company Nickname already used: " + str(self.company_nickname))
        if (len(records) == 1 and records[0].id != self.id):
            raise ValidationError(
                "Company Nickname already used: " + str(self.company_nickname))
