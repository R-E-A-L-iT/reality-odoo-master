# -*- coding: utf-8 -*-

import ast
import base64
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)

class StockLot(models.Model):
    _inherit = "stock.lot"

    # Store Data For CCP Tracking
    owner = fields.Many2one("res.partner", string="Owner")
    equipment_number = fields.Char(string="Equipment Number")
    sku = fields.Char(related="product_id.sku", readonly=True, string="SKU")
    expire = fields.Date(
        string="Expiration Date",
        default=lambda self: fields.Date.today(),
        required=False,
    )
    formated_label = fields.Char(compute="_label")
    publish = fields.Boolean(string="publish", default="True")

    ccp_status = fields.Selection(
        selection=[
            ("active", "Active"),
            ("expiring", "Expiring soon"),
            ("grace", "Grace period"),
            ("expired", "Expired"),
        ],
        string="Status",
        compute="_compute_ccp_status",
        store=False,
        readonly=True,
    )

    firmware_version = fields.Text(string='Firmware Version', help='Firmware version associated with this lot.')

    ccp_renewal_reminder_sent = fields.Boolean(
        string="CCP Renewal Reminder Sent", default=False, index=True
    )
    ccp_renewal_reminder_sent_on = fields.Datetime(
        string="CCP Reminder Sent On"
    )

    @api.depends("expire")
    def _compute_ccp_status(self):
        today = fields.Date.context_today(self)
        one_month = today + relativedelta(months=1)

        def _to_date(v):
            if not v:
                return None
            if isinstance(v, date):
                return v
            if isinstance(v, datetime):
                return v.date()
            return fields.Date.to_date(v)

        for lot in self:
            lot.ccp_status = False
            exp = _to_date(lot.expire)
            if not exp:
                continue

            if exp <= today:
                days_past = (today - exp).days
                lot.ccp_status = "grace" if days_past <= 7 else "expired"
            elif exp <= one_month:
                lot.ccp_status = "expiring"
            else:
                lot.ccp_status = "active"

    # Automate formated_label
    def _label(self):
        for i in self:
            parsedLabel = i.product_id.name.split(" - ")
            if len(parsedLabel) > 1:
                result = parsedLabel[1]
                for section in parsedLabel[2:]:
                    result = result + " - " + str(section)
                parsedLabel = result
            else:
                parsedLabel = parsedLabel[0]
            r = "#ccplabel+" + str(i.name) + "+" + str(parsedLabel)
            if i.expire != False:
                r = r + "+" + str(i.expire) 
            i.formated_label = r