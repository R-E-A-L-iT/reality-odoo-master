# -*- coding: utf-8 -*-
from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    activity_email_notify = fields.Boolean(
        string="Activity Assignment Emails",
        default=True,
        help="If enabled, you receive an email/notification whenever an "
             "activity is assigned to you. Disable it to stop those emails; "
             "assigned activities still show up in your Activities menu.",
    )

    # Allow users to read/write this preference on their own record without
    # needing administrator rights (used by the Preferences dialog).
    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["activity_email_notify"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["activity_email_notify"]
