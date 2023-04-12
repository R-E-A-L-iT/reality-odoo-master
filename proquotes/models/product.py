# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import RedirectWarning, AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.tools.translate import _
from odoo import models, fields, api


class product(models.Model):
    _inherit = "product.template"
    # productType = fields.Selection([
    # ('equipment', "Equipment"),
    # ('software', "Software")], default="equipment", required=True, string="Equipment/Software")
    cadVal = fields.Monetary(string="Canadian Product Value")
    usdVal = fields.Monetary(string="United States Product Value")
    type_selection = fields.Selection(
        [("H", "H"), ("S", "S"), ("SS", "SS")], string="Type (H/S/SS)", default=False)
    is_software = fields.Boolean(string="Is Software", default=False)
