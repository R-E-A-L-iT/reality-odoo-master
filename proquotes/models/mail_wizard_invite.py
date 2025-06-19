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

class MailWizardInvite(models.TransientModel):
    _inherit = 'mail.wizard.invite'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['notify'] = False  # always default to false
        return res

    def add_followers(self):
        self.ensure_one()
        self.notify = False  # force disable before executing
        return super().add_followers()