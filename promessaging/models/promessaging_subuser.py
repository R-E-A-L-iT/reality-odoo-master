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

    pin = fields.Char(
        string="PIN / API Key", groups="base.group_system",
        help="Secret this sub-user sends to identify itself. Actions carried out with "
             "it are attributed to this sub-user in the chatter.",
    )
    partner_id = fields.Many2one(
        "res.partner", string="Identity", readonly=True, copy=False,
        help="Contact used as the author of everything this sub-user does.",
    )
    image_1920 = fields.Image(string="Avatar", max_width=1024, max_height=1024)

    webhook_url = fields.Char(string="Webhook URL", groups="base.group_system")
    auth_key = fields.Char(
        string="Auth Key", groups="base.group_system",
        help="The key the receiver expects, sent in the header named below.",
    )
    auth_header = fields.Char(
        string="Auth Header", default="Authorization", groups="base.group_system",
        help="Header the key is sent in. Usually Authorization.",
    )
    auth_prefix = fields.Char(
        string="Auth Prefix", groups="base.group_system",
        help="Put before the key, e.g. Bearer. Leave empty to send the key on its own.",
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
    # identity and authentication
    # ------------------------------------------------------------------

    def _ensure_partner(self):
        """The contact every action of this sub-user is attributed to."""
        self.ensure_one()
        subuser = self.sudo()
        # an author without an email cannot post a comment, so fall back to the
        # owning user's address
        email = subuser.user_id.email or subuser.user_id.company_id.email or ""
        values = {
            "name": subuser.name,
            "email": email,
            "image_1920": subuser.image_1920 or False,
            "promessaging_subuser_id": subuser.id,
        }
        if subuser.partner_id:
            subuser.partner_id.write(values)
        else:
            partner = self.env["res.partner"].sudo().create(values)
            subuser.partner_id = partner.id
        return subuser.partner_id

    @api.model
    def _active_subuser(self):
        """The sub-user acting in this call, identified by its PIN in the context.

        The AI signs in as the shared account and adds
        {"subuser_handle": "jerry", "subuser_pin": "..."} to the call context.
        """
        context = self.env.context
        pin = context.get("subuser_pin")
        handle = context.get("subuser_handle")
        if not pin:
            return self.browse()

        domain = [("user_id", "=", self.env.uid)]
        if handle:
            domain.append(("handle", "=", str(handle).strip().lower()))
        for subuser in self.sudo().search(domain):
            if subuser.pin and hmac.compare_digest(str(subuser.pin), str(pin)):
                return subuser
        return self.browse()

    @api.model
    def authenticate(self, handle, pin):
        """Check a sub-user's credentials. Returns its identity, or False."""
        subuser = self.with_context(
            subuser_handle=handle, subuser_pin=pin
        )._active_subuser()
        if not subuser:
            return False
        return {
            "id": subuser.id,
            "name": subuser.name,
            "handle": subuser.handle,
            "partner_id": subuser.sudo()._ensure_partner().id,
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
                'style="color:#C264B6;background-color:rgba(194,100,182,0.16);'
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
        auth_key = (subuser.auth_key or "").strip()
        if auth_key:
            header_name = (subuser.auth_header or "Authorization").strip()
            prefix = (subuser.auth_prefix or "").strip()
            headers[header_name] = "%s %s" % (prefix, auth_key) if prefix else auth_key
        if subuser.webhook_secret:
            headers["X-REAL-Signature"] = hmac.new(
                subuser.webhook_secret.encode("utf-8"), body, hashlib.sha256
            ).hexdigest()

        log.write({"request_url": url, "request_headers": self._masked_headers(headers)})

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
            # surface it in the server log too: the body usually says why
            _logger.warning(
                "ProMessaging: webhook for ~%s -> HTTP %s\n  url: %s\n  sent headers: %s\n  response: %s",
                subuser.handle, response.status_code, url,
                self._masked_headers(headers).replace("\n", " | "),
                (response.text or "")[:1000] or "<empty body>",
            )
            log.write({"state": "error", "error": _("HTTP %s", response.status_code)})
            return {"ok": False, "error": "http_%s" % response.status_code}

        try:
            data = response.json() if response.text else {}
        except ValueError:
            data = {}
        log.write({"state": "done"})
        return {"ok": True, "data": data if isinstance(data, dict) else {}}

    @api.model
    def _masked_headers(self, headers):
        """Headers as sent, with the secret parts shortened."""
        sensitive = ("authorization", "x-real-signature", "x-api-key", "api-key", "token")
        lines = []
        for name, value in headers.items():
            shown = value
            if name.lower() in sensitive and len(value) > 12:
                shown = "%s…%s (%s chars)" % (value[:8], value[-4:], len(value))
            lines.append("%s: %s" % (name, shown))
        return "\n".join(lines)

    def action_test_webhook(self):
        """Send a ping so the credentials can be checked without posting a note."""
        self.ensure_one()
        result = self.dispatch("ping", {"message": "Test call from Odoo."})
        log = self.env["promessaging.webhook.log"].sudo().search(
            [("subuser_id", "=", self.id)], order="id desc", limit=1
        )
        if result.get("ok"):
            title, message, kind = _("Webhook reached"), _("%s answered.", self.name), "success"
        else:
            title = _("Webhook failed")
            message = _("%(error)s — open the call log for the full response.",
                        error=result.get("error") or _("unknown error"))
            kind = "danger"
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": title,
                "message": message,
                "type": kind,
                "sticky": not result.get("ok"),
                "next": {
                    "type": "ir.actions.act_window",
                    "res_model": "promessaging.webhook.log",
                    "res_id": log.id,
                    "view_mode": "form",
                    "views": [(False, "form")],
                } if log else {"type": "ir.actions.act_window_close"},
            },
        }

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
        author = self._ensure_partner() or self.user_id.partner_id
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
