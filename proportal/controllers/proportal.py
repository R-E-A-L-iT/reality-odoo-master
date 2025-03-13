# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal as CP
from odoo.addons.portal.controllers.portal import (
    pager as portal_pager,
    get_records_pager,
)
from odoo.osv import expression


class CustomerPortal(CP):
    # Create product page in the portal
    @http.route(
        ["/my/products", "/my/products/page/<int:page>"],
        type="http",
        auth="user",
        website=True,
    )
    def products(self):
        company = request.env.user.partner_id.parent_id
        values = {"company": company}
        return request.render("proportal.portal_products", values)
