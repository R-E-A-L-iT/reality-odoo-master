from odoo import models


class AccountMoveSend(models.TransientModel):
    _inherit = "account.move.send"

    # invoice "Send & Print": printing stays allowed, emailing does not
    def action_send_and_print(self, force_synchronous=False, allow_fallback_pdf=False, **kwargs):
        if any(self.mapped("checkbox_send_mail")):
            self.env["res.users"]._promessaging_check_send_message()
        return super().action_send_and_print(
            force_synchronous=force_synchronous, allow_fallback_pdf=allow_fallback_pdf, **kwargs
        )
