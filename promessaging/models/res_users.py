import logging

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError

_logger = logging.getLogger(__name__)
from odoo.http import request


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

    no_ping = fields.Boolean(
        string="Cannot Be Pinged",
        help="Hides this user from @mention lists and from Direct Messages, and stops "
             "anyone notifying them that way. They can still write to other people.",
    )

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

    def _get_company_ids(self):
        """Companies available right now.

        env.companies validates against this, so narrowing it here is what stops a
        sub-user reaching a company its profile excludes.
        """
        company_ids = super()._get_company_ids()
        if self.env.su or not self.id or self.id != self.env.uid:
            return company_ids
        # resolving the sub-user reads records, which can evaluate company rules
        # and land back here; one level is enough
        if getattr(request, "_promessaging_resolving_companies", False):
            return company_ids
        try:
            request._promessaging_resolving_companies = True
        except Exception:
            pass
        try:
            subuser = self.env["promessaging.subuser"]._active_subuser()
        finally:
            try:
                request._promessaging_resolving_companies = False
            except Exception:
                pass
        allowed = subuser._effective_companies() if subuser else None
        if not allowed:
            return company_ids
        # intersection: never a company the account itself lacks
        narrowed = tuple(cid for cid in company_ids if cid in set(allowed.ids))
        return narrowed or company_ids[:1]

    @api.model
    def has_group(self, group_ext_id):
        # @api.model matches the base signature: without it, call_kw dispatches
        # this as a record method and the argument never arrives
        result = super().has_group(group_ext_id)
        if not result or self.env.su:
            return result
        # only the user actually acting is limited, not lookups about other users
        if self.id and self.id != self.env.uid:
            return result
        subuser = self.env["promessaging.subuser"]._active_subuser()
        groups = subuser._effective_groups() if subuser else None
        if not groups:
            return result
        group = self.env.ref(group_ext_id, raise_if_not_found=False)
        return bool(group) and group in groups

    def _init_messaging(self):
        """Drop chats with people who cannot be reached from the sidebar."""
        values = super()._init_messaging()
        channels = values.get("channels")
        if not channels:
            return values
        ids = [channel["id"] for channel in channels if channel.get("id")]
        blocked = self.env["discuss.channel"].sudo().browse(ids)._promessaging_blocked_chats()
        if blocked:
            hidden = set(blocked.ids)
            values["channels"] = [c for c in channels if c.get("id") not in hidden]
        return values

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
    def _promessaging_allowed_author_ids(self):
        """Partners the current user may post as: itself, or its acting sub-user."""
        allowed = {self.env.user.partner_id.id}
        subuser = self.env["promessaging.subuser"]._active_subuser()
        if subuser and subuser.sudo().partner_id:
            allowed.add(subuser.sudo().partner_id.id)
        return allowed

    @api.model
    def _promessaging_check_author(self, author_id, email_from=None):
        """Refuse posting under someone else's name.

        Restricted accounts and AI accounts otherwise reach a customer simply by
        naming a colleague as the author.
        """
        user = self.env.user
        if self.env.su or not user._is_internal():
            return
        if not (user.is_ai_user or not user.can_send_message):
            return
        if author_id and author_id not in self._promessaging_allowed_author_ids():
            author = self.env["res.partner"].sudo().browse(author_id)
            _logger.warning(
                "ProMessaging: %s (uid %s) tried to post as %s",
                user.name, user.id, author.display_name,
            )
            raise AccessError(_(
                "You cannot post as %s. Messages are recorded under your own name.",
                author.display_name or author_id,
            ))
        if email_from:
            own = {
                (user.email or "").strip().lower(),
                (user.partner_id.email_formatted or "").strip().lower(),
                (user.email_formatted or "").strip().lower(),
            }
            subuser = self.env["promessaging.subuser"]._active_subuser()
            if subuser:
                own.add((subuser.sudo().partner_id.email_formatted or "").strip().lower())
            if str(email_from).strip().lower() not in {o for o in own if o}:
                _logger.warning(
                    "ProMessaging: %s (uid %s) tried to send from %s",
                    user.name, user.id, email_from,
                )
                raise AccessError(_(
                    "You cannot send from %s.", email_from,
                ))

    @api.model
    def _promessaging_guard_outgoing(self, what="message"):
        """The single gate every customer-facing path goes through."""
        if not self._promessaging_is_restricted():
            return
        user = self.env.user
        _logger.warning(
            "ProMessaging: blocked %s attempt by %s (uid %s)", what, user.name, user.id,
        )
        raise AccessError(_(
            "You are not allowed to send messages to customers. "
            "Write a draft instead: someone who may send will review it."
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
