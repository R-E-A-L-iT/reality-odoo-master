from odoo import models


class MailActivityMixin(models.AbstractModel):
    _inherit = "mail.activity.mixin"

    # "Send" button on activities with a mail template
    def activity_send_mail(self, template_id):
        self.env["res.users"]._promessaging_check_send_message()
        return super().activity_send_mail(template_id)
