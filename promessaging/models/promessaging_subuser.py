import hashlib
import hmac
import json
import logging
import re
import uuid
from datetime import datetime

import requests
from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

# the character that pings a sub-user, kept distinct from the "@" of real users
MENTION_PREFIX = "~"
MENTION_RE = re.compile(r"(?<![\w~])~([A-Za-z0-9][A-Za-z0-9_.-]{0,62})")
HANDLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,62}$")

PAYLOAD_VERSION = "1.0"

# request kinds an integration can receive; extend as new ones appear
WEBHOOK_TYPE_PROMPT = "prompt"
WEBHOOK_TYPE_LEAD_LOG = "lead_log"
WEBHOOK_TYPES = [
    (WEBHOOK_TYPE_PROMPT, "Prompt (message from a user)"),
    (WEBHOOK_TYPE_LEAD_LOG, "Lead logging request"),
]


class PromessagingSubuser(models.Model):
    """A named persona belonging to an AI user. Pinging it with ~handle sends the
    message to its webhook as a prompt."""
    _name = "promessaging.subuser"
    _description = "AI Sub-user"
    _order = "user_id, name"

    name = fields.Char(required=True)
    handle = fields.Char(
        required=True,
        help="What you type after ~ to ping this sub-user. Letters, digits, _ . - only.",
    )
    user_id = fields.Many2one(
        "res.users", string="AI User", required=True, ondelete="cascade", index=True,
        domain=[("is_ai_user", "=", True)],
        help="The AI user this sub-user belongs to. Replies are posted as that user.",
    )
    active = fields.Boolean(default=True)
    description = fields.Text(
        help="What this sub-user is for. Sent to the webhook so the bot knows its role."
    )

    webhook_url = fields.Char(string="Webhook URL", groups="base.group_system")
    webhook_token = fields.Char(
        string="Bearer Token", groups="base.group_system",
        help="Sent as 'Authorization: Bearer <token>' when set.",
    )
    webhook_secret = fields.Char(
        string="Signing Secret", groups="base.group_system",
        help="When set, the body is signed with HMAC-SHA256 in the X-REAL-Signature header.",
    )
    webhook_timeout = fields.Integer(string="Timeout (seconds)", default=20, groups="base.group_system")
    post_reply = fields.Boolean(
        string="Post Replies", default=True,
        help="When the webhook answers with a \"reply\", post it as a log note on the document.",
    )

    log_ids = fields.One2many(
        "promessaging.webhook.log", "subuser_id", string="Webhook Calls",
        groups="base.group_system",
    )
    log_count = fields.Integer(compute="_compute_log_count")

    _sql_constraints = [
        ("promessaging_subuser_handle_unique", "unique(handle)",
         "That sub-user handle is already taken."),
    ]

    def _compute_log_count(self):
        counts = {}
        if self.ids:
            groups = self.env["promessaging.webhook.log"].sudo().read_group(
                [("subuser_id", "in", self.ids)], ["subuser_id"], ["subuser_id"]
            )
            counts = {group["subuser_id"][0]: group["subuser_id_count"] for group in groups}
        for subuser in self:
            subuser.log_count = counts.get(subuser.id, 0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("handle"):
                vals["handle"] = vals["handle"].strip().lower()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("handle"):
            vals["handle"] = vals["handle"].strip().lower()
        return super().write(vals)

    @api.constrains("handle")
    def _check_handle(self):
        for subuser in self:
            if not HANDLE_RE.match(subuser.handle or ""):
                raise UserError(_(
                    "The handle %s is not valid. Use letters, digits, _ . - and no spaces.",
                    subuser.handle,
                ))

    @api.constrains("user_id")
    def _check_user_is_ai(self):
        for subuser in self:
            if not subuser.user_id.is_ai_user:
                raise UserError(_(
                    "%s is not marked as an AI user, so it cannot have sub-users.",
                    subuser.user_id.display_name,
                ))

    def action_view_logs(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Webhook Calls"),
            "res_model": "promessaging.webhook.log",
            "view_mode": "tree,form",
            "domain": [("subuser_id", "=", self.id)],
            "context": {"default_subuser_id": self.id},
        }

    # ------------------------------------------------------------------
    # mentions
    # ------------------------------------------------------------------

    @api.model
    def get_mention_suggestions(self, search="", limit=8):
        """Sub-users matching what was typed after ~, for the composer."""
        domain = [("user_id.is_ai_user", "=", True)]
        if search:
            domain += ["|", ("handle", "ilike", search), ("name", "ilike", search)]
        subusers = self.sudo().search(domain, limit=min(int(limit or 8), 20))
        return [
            {"id": s.id, "name": s.name, "handle": s.handle, "description": s.description or ""}
            for s in subusers
        ]

    @api.model
    def _highlight_mentions(self, body):
        """Wrap every ~handle of a real sub-user so it reads as a ping, not text."""
        body = body or ""
        if MENTION_PREFIX not in str(body):
            return body
        if "o_promessaging_mention" in str(body):
            return body  # already highlighted, don't nest
        handles = {
            subuser.handle: subuser
            for subuser in self.sudo().search([("user_id.is_ai_user", "=", True)])
        }
        if not handles:
            return body

        def replace(match):
            subuser = handles.get(match.group(1).lower())
            if not subuser:
                return match.group(0)
            return (
                '<span class="o_promessaging_mention" '
                'style="color:#714B67;background-color:rgba(113,75,103,0.12);'
                'border-radius:3px;padding:0 3px;font-weight:600;" '
                'data-oe-model="promessaging.subuser" data-oe-id="%s">~%s</span>'
            ) % (subuser.id, escape(subuser.handle))

        highlighted = MENTION_RE.sub(replace, str(body))
        return Markup(highlighted)

    @api.model
    def _find_mentioned(self, text):
        """Sub-users pinged in a piece of text."""
        handles = {match.lower() for match in MENTION_RE.findall(text or "")}
        if not handles:
            return self.browse()
        return self.sudo().search([("handle", "in", list(handles))])

    # ------------------------------------------------------------------
    # webhooks
    # ------------------------------------------------------------------

    def _webhook_envelope(self, payload_type, payload, record=None, actor=None):
        """The JSON every webhook call is wrapped in, whatever its type."""
        self.ensure_one()
        actor = actor or self.env.user
        envelope = {
            "version": PAYLOAD_VERSION,
            "type": payload_type,
            "event_id": str(uuid.uuid4()),
            "sent_at": datetime.utcnow().isoformat() + "Z",
            "odoo": {
                "base_url": self.get_base_url(),
                "database": self.env.cr.dbname,
                "company": {"id": self.env.company.id, "name": self.env.company.name},
            },
            "subuser": {
                "id": self.id,
                "name": self.name,
                "handle": self.handle,
                "description": self.description or "",
                "ai_user": {"id": self.user_id.id, "name": self.user_id.name},
            },
            "actor": {
                "user_id": actor.id,
                "name": actor.name,
                "login": actor.login,
                "email": actor.email or "",
            },
            "context": self._record_context(record),
            "payload": payload,
        }
        return envelope

    @api.model
    def _record_context(self, record):
        if record is None or not record:
            return False
        return {
            "model": record._name,
            "id": record.id,
            "name": record.sudo().display_name,
            "url": "%s/web#model=%s&id=%s&view_type=form" % (
                record.get_base_url(), record._name, record.id,
            ),
        }

    def dispatch(self, payload_type, payload, record=None, actor=None):
        """Send one webhook call. Never raises: failures are logged and returned."""
        self.ensure_one()
        subuser = self.sudo()
        Log = self.env["promessaging.webhook.log"].sudo()

        envelope = subuser._webhook_envelope(payload_type, payload, record=record, actor=actor)
        log = Log.create({
            "subuser_id": subuser.id,
            "webhook_type": payload_type,
            "event_id": envelope["event_id"],
            "res_model": record._name if record else False,
            "res_id": record.id if record else False,
            "request_body": json.dumps(envelope, ensure_ascii=False, indent=2),
            "state": "pending",
        })

        url = (subuser.webhook_url or "").strip()
        if not url:
            log.write({"state": "error", "error": _("No webhook URL configured on this sub-user.")})
            return {"ok": False, "error": "no_webhook_url"}

        body = json.dumps(envelope, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Odoo-17/ProMessaging",
            "X-REAL-Event": envelope["event_id"],
            "X-REAL-Type": payload_type,
        }
        if subuser.webhook_token:
            headers["Authorization"] = "Bearer %s" % subuser.webhook_token
        if subuser.webhook_secret:
            headers["X-REAL-Signature"] = hmac.new(
                subuser.webhook_secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()

        try:
            response = requests.post(
                url, data=body, headers=headers, timeout=subuser.webhook_timeout or 20
            )
        except requests.RequestException as error:
            _logger.warning("ProMessaging: webhook to %s failed: %s", subuser.handle, error)
            log.write({"state": "error", "error": str(error)})
            return {"ok": False, "error": str(error)}

        log.write({
            "status_code": response.status_code,
            "response_body": (response.text or "")[:20000],
        })
        if response.status_code >= 300:
            log.write({"state": "error", "error": _("HTTP %s", response.status_code)})
            return {"ok": False, "error": "http_%s" % response.status_code}

        try:
            data = response.json() if response.text else {}
        except ValueError:
            data = {}
        log.write({"state": "done"})
        return {"ok": True, "data": data if isinstance(data, dict) else {}}

    def notify_prompt(self, message, record):
        """A user pinged this sub-user in a message: send it as a prompt."""
        self.ensure_one()
        body_text = self._html_to_text(message.body)
        payload = {
            "prompt": MENTION_RE.sub(lambda m: m.group(1), body_text).strip(),
            "raw_text": body_text,
            "message": {
                "id": message.id,
                "body_html": message.body or "",
                "posted_at": fields.Datetime.to_string(message.date),
                "is_note": message.subtype_id == self.env.ref("mail.mt_note", raise_if_not_found=False),
                "author": {
                    "partner_id": message.author_id.id,
                    "name": message.author_id.display_name,
                },
            },
            "reply": {
                "mode": "chatter_note",
                "thread_model": record._name if record else False,
                "thread_id": record.id if record else False,
                "how": "Answer with JSON {\"reply\": \"text\"} to have it posted as a log note.",
            },
        }
        result = self.dispatch(WEBHOOK_TYPE_PROMPT, payload, record=record)
        reply = (result.get("data") or {}).get("reply") if result.get("ok") else None
        if reply and self.post_reply and record:
            self._post_reply(record, reply)
        return result

    def _post_reply(self, record, reply):
        """Post the bot's answer as a log note, authored by the AI user."""
        self.ensure_one()
        author = self.user_id.partner_id
        body = "<b>%s</b><br/>%s" % (
            self.name, "<br/>".join(str(reply).splitlines()),
        )
        record.sudo().with_context(promessaging_skip_subuser_dispatch=True).message_post(
            body=body,
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=author.id or self.env.ref("base.partner_root").id,
        )

    @api.model
    def _html_to_text(self, html):
        text = re.sub(r"<br\s*/?>", "\n", html or "")
        text = re.sub(r"</p>", "\n", text)
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\n{3,}", "\n\n", text).strip()
