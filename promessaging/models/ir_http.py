from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        user = self.env.user
        if user._is_internal():
            result["can_send_message"] = user.can_send_message
        return result
