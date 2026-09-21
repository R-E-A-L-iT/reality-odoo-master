from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    is_ai_user = fields.Boolean(
        string="AI User",
        help="Marks this account as an AI. AI users can have sub-users, each pinged "
             "with ~handle in a message.",
    )
    promessaging_default_subuser_id = fields.Many2one(
        "promessaging.subuser", string="Default AI Assistant",
        groups="base.group_system", ondelete="set null",
        help="Used when a request needs a bot and none is already assigned, "
             "for instance rewriting a draft nobody wrote.",
    )

    # counted through sudo on purpose: res.users records are read in contexts
    # (portal, public) that have no access to promessaging.subuser
    subuser_count = fields.Integer(compute="_compute_subuser_count")

    can_send_message = fields.Boolean(
        string="Can Send Messages",
        default=True,
        help="Allows this internal user to send messages and emails from the chatter of any document. "
             "When unchecked, the user can still log notes and mention internal users.",
    )

    def _compute_subuser_count(self):
        counts = {}
        if self.ids:
            groups = self.env["promessaging.subuser"].sudo().read_group(
                [("user_id", "in", self.ids)], ["user_id"], ["user_id"]
            )
            counts = {group["user_id"][0]: group["user_id_count"] for group in groups}
        for user in self:
            user.subuser_count = counts.get(user.id, 0)

    def _promessaging_default_subuser(self):
        """This user's default assistant, if they are allowed to use it."""
        self.ensure_one()
        subuser = self.sudo().promessaging_default_subuser_id
        return subuser._allowed_for(self) if subuser else subuser

    def action_view_subusers(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("AI Sub-users"),
            "res_model": "promessaging.subuser",
            "view_mode": "tree,form",
            "domain": [("user_id", "=", self.id)],
            "context": {"default_user_id": self.id},
        }

    @api.model
    def _promessaging_is_restricted(self):
        user = self.env.user
        return not self.env.su and user._is_internal() and not user.can_send_message

    @api.model
    def _promessaging_check_send_message(self):
        """Raise if the current user is not allowed to send messages."""
        if self._promessaging_is_restricted():
            raise UserError(_(
                "You are not allowed to send messages from documents. "
                "You can still log a note and mention internal users."
            ))

    @api.model
    def _promessaging_check_note_recipients(self, partners, emails=()):
        """Restricted users may only mention internal users in notes, since a
        mention notifies the partner by email."""
        if not self._promessaging_is_restricted():
            return
        external = partners.sudo().filtered(
            lambda p: not any(u._is_internal() for u in p.with_context(active_test=False).user_ids)
        )
        names = external.mapped("display_name") + list(emails)
        if names:
            raise UserError(_(
                "You can only mention internal users in a note. Remove: %s"
            ) % ", ".join(names))
