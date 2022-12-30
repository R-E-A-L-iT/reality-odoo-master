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


class stock(models.Model):
	_inherit = "stock.picking"

	footer = fields.Selection([
		('ABtechFooter_Atlantic_Ryan', "Abtech_Atlantic_Ryan"),
		('ABtechFooter_Ontario_Phil', "Abtech_Ontario_Phil"),
		('ABtechFooter_Quebec_Benoit_Carl', "ABtechFooter_Quebec_Benoit_Carl"),
		('ABtechFooter_Quebec_Derek', "Abtech_Quebec_Derek"),
		('Geoplus_Canada', "Geoplus_Canada"),
		('Geoplus_America', "Geoplus_America"),
		('Leica_Various_Ali', "Leica_Various_Ali"),
		('REALiTFooter_Derek_US', "REALiTFooter_Derek_US"),
		('REALiTFooter_Derek', "REALiTFooter_Derek")], default='REALiTFooter_Derek', required=True, help="Footer selection field")
