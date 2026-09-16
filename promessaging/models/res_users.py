from odoo import _, api, fields, models
from odoo.exceptions import UserError


class ResUsers(models.Model):
    _inherit = "res.users"

    is_ai_user = fields.Boolean(
        string="AI User",
        help="Marks this account as an AI. AI users can have sub-users, each pinged "
             "with ~handle in a message.",
    )
    subuser_ids = fields.One2many(
        "promessaging.subuser", "user_id", string="Sub-users",
    )

    can_send_message = fields.Boolean(
        string="Can Send Messages",
        default=True,
        help="Allows this internal user to send messages and emails from the chatter of any document. "
             "When unchecked, the user can still log notes and mention internal users.",
    )

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
