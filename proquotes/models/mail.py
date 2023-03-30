# -*- coding: utf-8 -*-

import ast
import base64
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


class mail(models.TransientModel):
    _inherit = "mail.compose.message"

    def get_mail_values(self, res_ids):
        result = super().get_mail_values(res_ids)
        _logger.warning(result)
        _logger.error(len(result))
        # _logger.warning(result['email_from'])
        # _logger.warning(result['reply_to'])
        return result
