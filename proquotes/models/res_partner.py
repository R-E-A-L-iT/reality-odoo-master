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

class person(models.Model):
    _inherit = "res.partner"

    # proportal owns the compute. Repeat it here so this later override
    # does not drop back to a plain inverse One2many (which ignores rules).
    products = fields.One2many(
        "stock.lot",
        "owner",
        string="Products",
        compute="_compute_customer_products",
        compute_sudo=False,
        readonly=True,
    )