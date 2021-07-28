# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager, get_records_pager
from odoo.addons.sale.controllers.portal import CustomerPortal as sourcePortal
from odoo.osv import expression


class CustomerPortal(sourcePortal):

    #
    # Quotations and Sales Orders
    #
    def _prepare_portal_layout_values(self):
        raise UserError(_("Override"))
