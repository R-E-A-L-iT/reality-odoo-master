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


class company(models.Model):
    _inherit = "res.company"
    logo_url = fields.Char(
        string="Logo URL", default="https://cdn.r-e-a-l.it//images/icons/REALiT-Header.gif", required="True")
    header_footer_ids = fields.Many2many(
        "header.footer", string="Invoice Footer List")
    prefered_invoice_footers = fields.Many2many(
        "header.footer", column1="invoicefooter", string="Invoice Footer List")
