from odoo import api, models


class AccountMoveSend(models.AbstractModel):
    _inherit = "account.move.send"

    @api.model
    def _send_mail(self, move, mail_template, **kwargs):
        """Last door for invoice email, including the background batch cron."""
        self.env["res.users"]._promessaging_guard_outgoing("invoice email")
        return super()._send_mail(move, mail_template, **kwargs)


class AccountMoveSendWizard(models.TransientModel):
    _inherit = "account.move.send.wizard"

    # invoice "Send & Print": printing stays allowed, emailing does not
    def action_send_and_print(self, allow_fallback_pdf=False):
        if "email" in (self.sending_methods or []):
            self.env["res.users"]._promessaging_check_send_message()
        return super().action_send_and_print(allow_fallback_pdf=allow_fallback_pdf)


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = "account.move.send.batch.wizard"

    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False):
        # batch sending always delivers; there is no download-only path
        self.env["res.users"]._promessaging_check_send_message()
        return super().action_send_and_print(
            force_synchronous=force_synchronous,
            allow_fallback_pdf=allow_fallback_pdf,
        )
