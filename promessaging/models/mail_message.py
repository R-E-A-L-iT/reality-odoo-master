from odoo import api, fields, models


class MailMessage(models.Model):
    _inherit = "mail.message"

    subuser_id = fields.Many2one(
        "promessaging.subuser", string="AI Sub-user", ondelete="set null", index=True,
        groups="base.group_user",
        help="The AI sub-user that produced this message, when one was acting.",
    )

    @api.model_create_multi
    def create(self, vals_list):
        # stamp everything written while a sub-user is acting, including the
        # tracking messages Odoo posts by itself
        subuser = self.env["promessaging.subuser"]._active_subuser()
        if subuser:
            for vals in vals_list:
                vals.setdefault("subuser_id", subuser.id)
        return super().create(vals_list)
