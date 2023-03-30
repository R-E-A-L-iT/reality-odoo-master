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
        for key in result:
            _logger.error(key)

            for key2 in result[key]:
                _logger.error(str(key2) + str(result[key][key2]))
            # result[key]['reply_to'] = result[key]['email_from']
            result[key]['reply_to_mode'] = 'new'
            # result[key]['reply_to_force_new'] = True
        return result
