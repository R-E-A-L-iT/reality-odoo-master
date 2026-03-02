# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    allowed_quo_phone_number_ids = fields.Many2many(
        "quo.phone.number",
        "res_users_quo_phone_rel",
        "user_id",
        "phone_id",
        string="Allowed Quo Numbers",
        help="Quo numbers this user is allowed to send SMS from.",
    )