from odoo import models


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def unlink(self):
        # a deleted document must not leave its draft behind
        self.env["promessaging.draft"].sudo().search([
            ("res_model", "=", self._name), ("res_id", "in", self.ids),
        ]).unlink()
        return super().unlink()
