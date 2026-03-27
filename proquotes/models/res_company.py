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
	_inherit = "res.company"
	
	logo_url = fields.Char(
		string="Logo URL",
		default="https://cdn.r-e-a-l.it//images/icons/REALiT-Header.gif",
		required="True",
	)
	
	default_footer_id = fields.Many2one(
		"header.footer",
		string="Default Footer",
		domain="[('active', '=', True), ('record_type', '=', 'Footer')]",
	)

	def write(self, values):
		if 'parent_id' in values:
			parent_id_val = values.pop('parent_id')
			res = super().write(values) if values else True
			if parent_id_val is not False and parent_id_val is not None:
				self.env.cr.execute(
					"UPDATE res_company SET parent_id = %s WHERE id IN %s",
					(parent_id_val, tuple(self.ids))
				)
			else:
				self.env.cr.execute(
					"UPDATE res_company SET parent_id = NULL WHERE id IN %s",
					(tuple(self.ids),)
				)
			self.env['res.company']._parent_store_compute()
			self.invalidate_recordset()
			return res
		return super().write(values)

	def _check_root_delegated_fields(self):
		"""Allow multi-currency/multi-fiscal branches during hierarchy setup."""
		return
