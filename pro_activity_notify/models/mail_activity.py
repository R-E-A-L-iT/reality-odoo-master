# -*- coding: utf-8 -*-
from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def action_notify(self):
        """Skip the assignment notification for users who opted out.

        ``action_notify`` is the single method Odoo core calls to email the
        assignee, both when an activity is created and when it is reassigned
        (see ``mail.activity.create`` / ``write``). We simply drop the
        activities whose assignee disabled ``activity_email_notify`` before
        letting core do its work.
        """
        activities = self.filtered(lambda act: act.user_id.activity_email_notify)
        return super(MailActivity, activities).action_notify()
