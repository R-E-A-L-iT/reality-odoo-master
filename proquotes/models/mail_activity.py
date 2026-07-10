# -*- coding: utf-8 -*-

from odoo import models


class MailActivity(models.Model):
    _inherit = "mail.activity"

    def _action_notify(self):
        """Skip the activity-assignment notification for users who turned off
        activity email notifications (res.users.activity_send_email). The
        activity itself is still created and shows in their Activities menu."""
        notifiable = self.filtered(lambda a: a.user_id and a.user_id.activity_send_email)
        return super(MailActivity, notifiable)._action_notify()
