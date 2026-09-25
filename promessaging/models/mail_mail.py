from odoo import api, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    @api.model_create_multi
    def create(self, vals_list):
        # the last door: building a mail by hand and sending it
        reaches_outside = any(
            vals.get("email_to") or vals.get("recipient_ids") or vals.get("email_cc")
            for vals in vals_list
        )
        if reaches_outside:
            self.env["res.users"]._promessaging_guard_outgoing("email")
        return super().create(vals_list)


class MailTemplate(models.Model):
    _inherit = "mail.template"

    def send_mail(self, res_id, force_send=False, raise_exception=False,
                  email_values=None, email_layout_xmlid=False):
        self.env["res.users"]._promessaging_guard_outgoing("template email")
        return super().send_mail(
            res_id, force_send=force_send, raise_exception=raise_exception,
            email_values=email_values, email_layout_xmlid=email_layout_xmlid,
        )
