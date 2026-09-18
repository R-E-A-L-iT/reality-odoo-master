import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

HISTORY_LIMIT = 20


class PromessagingAiChat(models.Model):
    """A private conversation between one person and one AI sub-user."""
    _name = "promessaging.ai.chat"
    _description = "AI Chat Conversation"
    _order = "write_date desc"

    user_id = fields.Many2one(
        "res.users", string="User", required=True, index=True, ondelete="cascade",
        default=lambda self: self.env.user,
    )
    subuser_id = fields.Many2one(
        "promessaging.subuser", string="AI Sub-user", required=True, index=True, ondelete="cascade",
    )
    message_ids = fields.One2many("promessaging.ai.chat.message", "chat_id", string="Messages")

    _sql_constraints = [
        ("promessaging_ai_chat_unique", "unique(user_id, subuser_id)",
         "There is already a conversation with this sub-user."),
    ]

    # ------------------------------------------------------------------
    # directory and opening
    # ------------------------------------------------------------------

    @api.model
    def get_directory(self):
        """The AI sub-users the current user can talk to."""
        acting = self.env["promessaging.subuser"]._active_subuser()
        subusers = self.env["promessaging.subuser"].sudo().search([
            ("user_id.is_ai_user", "=", True),
            ("id", "!=", acting.id or 0),
        ])
        return [
            {
                "id": subuser.id,
                "name": subuser.name,
                "handle": subuser.handle,
                "description": subuser.description or "",
                "avatar": "/web/image/promessaging.subuser/%s/image_1920/40x40" % subuser.id,
                "has_avatar": bool(subuser.image_1920),
                "initial": (subuser.name or "?")[:1].upper(),
            }
            for subuser in subusers
        ]

    @api.model
    def open_chat(self, subuser_id):
        """Get (or start) my conversation with a sub-user, with its history."""
        subuser = self.env["promessaging.subuser"].sudo().browse(int(subuser_id)).exists()
        if not subuser:
            raise UserError(_("That sub-user no longer exists."))
        if subuser == self.env["promessaging.subuser"]._active_subuser():
            raise UserError(_("A sub-user cannot open a conversation with itself."))
        chat = self.search([
            ("user_id", "=", self.env.uid), ("subuser_id", "=", subuser.id),
        ], limit=1)
        if not chat:
            chat = self.create({"user_id": self.env.uid, "subuser_id": subuser.id})
        return chat._chat_data()

    def _chat_data(self, after_id=0):
        self.ensure_one()
        messages = self.message_ids.filtered(lambda m: m.id > int(after_id or 0))
        return {
            "id": self.id,
            "subuser": {
                "id": self.subuser_id.id,
                "name": self.subuser_id.sudo().name,
                "handle": self.subuser_id.sudo().handle,
                "avatar": "/web/image/promessaging.subuser/%s/image_1920/40x40" % self.subuser_id.id,
                "has_avatar": bool(self.subuser_id.sudo().image_1920),
                "initial": (self.subuser_id.sudo().name or "?")[:1].upper(),
            },
            "messages": [message._message_data() for message in messages],
        }

    def fetch_messages(self, after_id=0):
        """Anything said since after_id, for the open window to catch up."""
        self.ensure_one()
        return self._chat_data(after_id=after_id)

    # ------------------------------------------------------------------
    # talking
    # ------------------------------------------------------------------

    def _history(self):
        self.ensure_one()
        messages = self.message_ids.sorted("id")[-HISTORY_LIMIT:]
        return [
            {
                "author": message.author,
                "name": message.display_author,
                "body": message.body or "",
                "at": fields.Datetime.to_string(message.create_date),
            }
            for message in messages
        ]

    def post_message(self, body):
        """Send a message to the sub-user and return whatever comes back."""
        self.ensure_one()
        body = (body or "").strip()
        if not body:
            return self._chat_data(after_id=self._last_id())
        last_id = self._last_id()
        Message = self.env["promessaging.ai.chat.message"]
        Message.create({
            "chat_id": self.id,
            "author": "user",
            "body": body,
            "user_id": self.env.uid,
        })

        subuser = self.subuser_id.sudo()
        payload = {
            "prompt": body,
            "conversation": {
                "id": self.id,
                "with": {"user_id": self.user_id.id, "name": self.user_id.name},
                "history": self._history(),
            },
            "reply": subuser._reply_instructions(chat_id=self.id),
        }
        result = subuser.dispatch("prompt", payload, record=None, actor=self.env.user)
        reply = (result.get("data") or {}).get("reply") if result.get("ok") else None
        if reply:
            self._create_ai_message(reply)
        elif not result.get("ok"):
            Message.create({
                "chat_id": self.id,
                "author": "system",
                "body": _("Could not reach %(name)s (%(error)s).",
                          name=subuser.name, error=result.get("error") or _("unknown error")),
            })
        return self._chat_data(after_id=last_id)

    def _create_ai_message(self, text):
        self.ensure_one()
        return self.env["promessaging.ai.chat.message"].sudo().create({
            "chat_id": self.id,
            "author": "ai",
            "body": str(text),
            "subuser_id": self.subuser_id.id,
        })

    @api.model
    def post_reply(self, chat_id, text):
        """Called by the AI to answer later, outside the webhook response."""
        chat = self.browse(int(chat_id)).exists()
        if not chat:
            raise UserError(_("That conversation no longer exists."))
        # readable by the owner, or by the account the sub-user belongs to
        chat.check_access_rights("read")
        chat.check_access_rule("read")
        chat._create_ai_message(text)
        return True

    def _last_id(self):
        self.ensure_one()
        return max(self.message_ids.ids or [0])


class PromessagingAiChatMessage(models.Model):
    _name = "promessaging.ai.chat.message"
    _description = "AI Chat Message"
    _order = "id"

    chat_id = fields.Many2one(
        "promessaging.ai.chat", required=True, index=True, ondelete="cascade",
    )
    author = fields.Selection(
        [("user", "User"), ("ai", "AI"), ("system", "System")], required=True, default="user",
    )
    body = fields.Text(required=True)
    user_id = fields.Many2one("res.users", string="Sent By")
    subuser_id = fields.Many2one("promessaging.subuser", string="AI Sub-user")
    display_author = fields.Char(compute="_compute_display_author")

    @api.depends("author", "user_id", "subuser_id")
    def _compute_display_author(self):
        for message in self:
            if message.author == "ai":
                message.display_author = message.subuser_id.sudo().name or _("AI")
            elif message.author == "system":
                message.display_author = _("System")
            else:
                message.display_author = message.user_id.name or _("You")

    def _message_data(self):
        self.ensure_one()
        return {
            "id": self.id,
            "author": self.author,
            "name": self.display_author,
            "body": self.body or "",
            "at": fields.Datetime.to_string(self.create_date),
        }
