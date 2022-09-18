# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.osv import expression
import logging

# from odoo.mail import CustomerPortalINH as CP


# class notification(CP):
# pass

class notification:
    def something():
        x = 1 + 1
