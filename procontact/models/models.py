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


class individual(models.Model):
    _inherit = 'res.partner'

    linkedin_link = fields.Char(
        string="LinkedIn link"
    )

    is_customer = fields.Boolean(
        string="Is Customer?",
        default=True,
        help="Check this box if this contact is a customer."
    )

    has_had_contact = fields.Boolean(
        string="Has had contact",
        default=True,
        help="Whether we have had contact with this person/company."
    )

    first_name = fields.Char(string="First Name", compute="_compute_first_last_names", store=False)
    last_name = fields.Char(string="Last Name", compute="_compute_first_last_names", store=False)

    parent_company_id = fields.Many2one(
        comodel_name="res.partner",
        string="Parent Company",
        domain="[('is_company', '=', True), ('id', '!=', id)]",
        help="Select the parent company for this company contact."
    )

    # NEW: Branches list (companies that point to this company as parent)
    branch_company_ids = fields.One2many(
        comodel_name="res.partner",
        inverse_name="parent_company_id",
        string="Branches",
        domain=[('is_company', '=', True)],
        readonly=True,
        help="Companies that have this company set as their Parent Company."
    )

    def _compute_first_last_names(self):
        for rec in self:
            parts = (rec.name or "").strip().split()
            rec.first_name = parts[0] if parts else ''
            rec.last_name = parts[-1] if len(parts) > 1 else rec.first_name
