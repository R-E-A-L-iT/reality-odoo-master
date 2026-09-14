from odoo import models


class MailComposeMessage(models.TransientModel):
    _inherit = "mail.compose.message"

    # covers the full chatter composer and "Send by Email" buttons on documents
    def _action_send_mail(self, auto_commit=False):
        Users = self.env["res.users"]
        for wizard in self:
            if wizard.composition_mode == "comment" and wizard.subtype_is_log:
                Users._promessaging_check_note_recipients(wizard.partner_ids)
            else:
                Users._promessaging_check_send_message()
        return super()._action_send_mail(auto_commit=auto_commit)
