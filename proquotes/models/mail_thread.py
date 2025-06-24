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

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals=msg_vals)

        if not self:
            return groups

        self.ensure_one()

        # Fetch access link (requires portal.mixin inheritance)
        if not isinstance(self, self.env.registry['portal.mixin']):
            return groups

        access_token = self._portal_ensure_token()
        access_link = self.get_portal_url()

        for group in groups:
            group_name, match_func, options = group

            if group_name == 'follower':
                options['active'] = True
                options['has_button_access'] = True
                options['button_access'] = {
                    'url': access_link,
                    'title': _('View Invoice') if self._name == 'account.move' else _('View Document')
                }

        return groups