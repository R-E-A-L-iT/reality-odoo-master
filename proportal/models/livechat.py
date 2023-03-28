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
from odoo.http import request
from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)


class livechat(models.Model):
    _inherit = "website.visitor"

    @api.depends('mail_channel_ids.livechat_active', 'mail_channel_ids.livechat_operator_id')
    def _compute_livechat_operator_id(self):
        _logger.error("ASSIGN LIVECHAT: request.lang")
        super()._compute_livechat_operator_id()
