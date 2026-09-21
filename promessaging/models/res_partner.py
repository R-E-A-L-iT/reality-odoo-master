from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    promessaging_subuser_id = fields.Many2one(
        "promessaging.subuser", string="AI Sub-user", readonly=True, copy=False, index=True,
        groups="base.group_user",
        help="Set on the contact that represents an AI sub-user in the chatter.",
    )
