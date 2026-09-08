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
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    ip_address = fields.Char(string="IP Address", help="The IP address of the visitor")