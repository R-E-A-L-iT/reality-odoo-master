import hmac
import json
import logging
import re
import uuid
from datetime import datetime

import requests
from markupsafe import Markup, escape

from odoo import _, api, fields, models
from odoo.http import request
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
    allowed_user_ids = fields.Many2many(
        "res.users", "promessaging_subuser_allowed_users_rel", "subuser_id", "user_id",
        string="Usable By",
        help="Users allowed to ping, message and assign this sub-user. "
             "Leave empty to let everyone use it.",
    )
    group_ids = fields.Many2many(
        "res.groups", "promessaging_subuser_groups_rel", "subuser_id", "group_id",
        string="Permissions", groups="base.group_system",
        help="What this sub-user may do. Leave empty and it simply inherits the AI "
             "account's own permissions. Otherwise its actions are limited to these "
             "groups as well as the account's, never beyond them.",
    )
    company_ids = fields.Many2many(
        "res.company", "promessaging_subuser_companies_rel", "subuser_id", "company_id",
        string="Allowed Companies", groups="base.group_system",
        help="Companies this sub-user may work in. Leave empty and it inherits the AI "
             "account's companies. Otherwise it is limited to these, and never gets a "
             "company the account itself lacks.",
    )
    company_id = fields.Many2one(
        "res.company", string="Default Company", groups="base.group_system",
        ondelete="set null",
        help="Company selected when this sub-user signs in.",
    )
    sync_user_id = fields.Many2one(
        "res.users", string="Mirror Permissions Of", groups="base.group_system",
        ondelete="set null",
        help="Copy this user's permissions onto the sub-user. Re-applied every time "
             "the sub-user signs in, so it keeps matching that user.",
    )
    permissions_synced_on = fields.Datetime(
        string="Permissions Synced", readonly=True, groups="base.group_system",
    )

    description = fields.Text(
        help="What this sub-user is for. Sent to the webhook so the bot knows its role."
    )

    inbound_key = fields.Char(
        string="Reply Key", groups="base.group_system", copy=False,
        default=lambda self: "pmsg_" + uuid.uuid4().hex,
        help="Secret this sub-user sends back when posting replies to "
             "/promessaging/webhook/reply.",
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

    webhook_url = fields.Char(
        string="POST to", groups="base.group_system",
        help="The webhook URL, copied from the receiver.",
    )
    auth_key = fields.Char(
        string="key", groups="base.group_system",
        help="The key, copied from the receiver. Kept for reference; the header "
             "below is what gets sent.",
    )
    auth_header = fields.Char(
        string="header", groups="base.group_system",
        help="The full header line, pasted exactly as the receiver shows it, "
             "e.g. 'Authorization: Bearer crsr_...'. A bare header name also works, "
             "in which case the key above is sent as its value.",
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
        subusers = super().create(vals_list)
        for subuser in subusers:
            subuser._ensure_partner()
        return subusers

    def write(self, vals):
        if vals.get("handle"):
            vals["handle"] = vals["handle"].strip().lower()
        result = super().write(vals)
        if "group_ids" in vals:
            self.env.registry.clear_cache()
        if not self.env.context.get("promessaging_building_identity") and (
            "name" in vals or "image_1920" in vals or "user_id" in vals
        ):
            for subuser in self:
                subuser._ensure_partner()
        return result

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
        """The contact every action of this sub-user is attributed to.

        Creating a partner posts tracking messages, which ask who the author is,
        so the identity flag keeps that from coming back here.
        """
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
        Partner = self.env["res.partner"].sudo().with_context(
            promessaging_building_identity=True
        )
        if subuser.partner_id:
            subuser.partner_id.with_context(promessaging_building_identity=True).write(values)
        else:
            subuser.with_context(promessaging_building_identity=True).partner_id = Partner.create(values).id
        subuser._cleanup_duplicate_identities()
        return subuser.partner_id

    def _cleanup_duplicate_identities(self):
        """Drop stray identity contacts, e.g. left by a failed run."""
        self.ensure_one()
        subuser = self.sudo()
        if not subuser.partner_id:
            return
        duplicates = self.env["res.partner"].sudo().search([
            ("promessaging_subuser_id", "=", subuser.id),
            ("id", "!=", subuser.partner_id.id),
        ])
        for partner in duplicates:
            try:
                partner.with_context(promessaging_building_identity=True).unlink()
            except Exception:
                # referenced somewhere: keep it, just get it out of the way
                partner.with_context(promessaging_building_identity=True).active = False

    @api.model
    def _active_subuser(self):
        """The sub-user acting right now.

        Either passed per call by an AI
        ({"subuser_handle": "jerry", "subuser_pin": "..."} in the context), or
        chosen once for the browser session through the PIN prompt.
        """
        context = self.env.context
        pin = context.get("subuser_pin")
        handle = context.get("subuser_handle")
        if pin:
            domain = [("user_id", "=", self.env.uid)]
            if handle:
                domain.append(("handle", "=", str(handle).strip().lower()))
            for subuser in self.sudo().search(domain):
                if subuser.pin and hmac.compare_digest(str(subuser.pin), str(pin)):
                    return subuser
            return self.browse()
        return self._session_subuser()

    @api.model
    def _session_subuser(self):
        """The sub-user this browser session signed in as, if any."""
        try:
            session = request.session if request else None
        except Exception:
            session = None
        if not session:
            return self.browse()
        subuser_id = session.get("promessaging_subuser_id")
        if not subuser_id:
            return self.browse()

        # this runs on every access check, so resolve it once per request
        key = (self.env.uid, subuser_id)
        cached = getattr(request, "_promessaging_subuser", None)
        if cached and cached[0] == key:
            return self.browse(cached[1]) if cached[1] else self.browse()

        subuser = self.sudo().browse(int(subuser_id)).exists()
        # the session is only valid for sub-users of the account that is logged in
        if not subuser or subuser.user_id.id != self.env.uid:
            subuser = self.browse()
        try:
            request._promessaging_subuser = (key, subuser.id or False)
        except Exception:
            pass
        return subuser

    @api.model
    def _verify_pin(self, subuser_id, pin):
        """Check a PIN against one sub-user of the current account."""
        subuser = self.sudo().browse(int(subuser_id or 0)).exists()
        if not subuser or subuser.user_id.id != self.env.uid:
            return self.browse()
        if not subuser.pin or not pin:
            return self.browse()
        if not hmac.compare_digest(str(subuser.pin), str(pin)):
            return self.browse()
        subuser._ensure_partner()
        subuser._sync_permissions()
        return subuser

    @api.model
    def get_session_state(self):
        """What the PIN prompt needs: who I am, and who I could be."""
        user = self.env.user
        options = self.sudo().search([("user_id", "=", user.id)])
        current = self._session_subuser()
        return {
            "is_ai_user": bool(user.is_ai_user),
            "required": bool(user.is_ai_user and options and not current),
            "current": {
                "id": current.id,
                "name": current.name,
                "handle": current.handle,
            } if current else False,
            "options": [
                {
                    "id": option.id,
                    "name": option.name,
                    "handle": option.handle,
                    "description": option.description or "",
                }
                for option in options
            ],
        }

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
    def _allowed_domain(self, user=None):
        """Restrict a search to the sub-users this user may use."""
        user = user or self.env.user
        return ["|", ("allowed_user_ids", "=", False), ("allowed_user_ids", "in", user.id)]

    def _allowed_for(self, user=None):
        """Sub-users of this set the user may use."""
        user = user or self.env.user
        return self.sudo().filtered(
            lambda s: not s.allowed_user_ids or user in s.allowed_user_ids
        )

    @api.model
    def get_mention_suggestions(self, search="", limit=8):
        """Sub-users matching what was typed after ~, for the composer."""
        domain = [("user_id.is_ai_user", "=", True)] + self._allowed_domain()
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
            for subuser in self.sudo().search(
                [("user_id.is_ai_user", "=", True)] + self._allowed_domain()
            )
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
        found = self.sudo().search([("handle", "in", list(handles))])
        # a bot the poster may not use is left as plain text, and never pinged
        return found._allowed_for()

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
        headers.update(subuser._auth_headers())

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

    def _auth_headers(self):
        """Whatever the receiver asked for, from the header line or the key."""
        self.ensure_one()
        subuser = self.sudo()
        header_line = (subuser.auth_header or "").strip()
        key = (subuser.auth_key or "").strip()

        # "Authorization: Bearer crsr_..." pasted whole
        if ":" in header_line:
            name, _separator, value = header_line.partition(":")
            if name.strip() and value.strip():
                return {name.strip(): value.strip()}
        # just a header name, with the key as its value
        if header_line and key:
            return {header_line: key}
        # nothing but a key: the common default
        if key:
            return {"Authorization": "Bearer %s" % key}
        return {}

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

    def action_sync_permissions(self):
        """Copy the mirrored user's permissions onto this sub-user."""
        for subuser in self:
            subuser._sync_permissions()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Permissions synced"),
                "message": _("The sub-user now matches its mirrored user."),
                "type": "success",
            },
        }

    def _sync_permissions(self, only_if_changed=True):
        """Bring group_ids in line with the mirrored user, if one is set."""
        self.ensure_one()
        subuser = self.sudo()
        source = subuser.sync_user_id
        if not source:
            return False
        wanted = source.groups_id
        wanted_companies = source.company_ids
        unchanged = (
            set(wanted.ids) == set(subuser.group_ids.ids)
            and set(wanted_companies.ids) == set(subuser.company_ids.ids)
            and subuser.company_id == source.company_id
        )
        if only_if_changed and unchanged:
            return False
        subuser.write({
            "group_ids": [(6, 0, wanted.ids)],
            "company_ids": [(6, 0, wanted_companies.ids)],
            "company_id": source.company_id.id,
            "permissions_synced_on": fields.Datetime.now(),
        })
        return True

    def _effective_companies(self):
        """The companies limiting this sub-user, or an empty set for no limit."""
        self.ensure_one()
        return self.sudo().company_ids

    def _effective_groups(self):
        """The groups limiting this sub-user, or an empty set for no limit."""
        self.ensure_one()
        return self.sudo().group_ids

    def action_regenerate_inbound_key(self):
        """Issue a new reply key, invalidating the old one."""
        for subuser in self:
            subuser.sudo().inbound_key = "pmsg_" + uuid.uuid4().hex
        return True

    @api.model
    def _authenticate_inbound(self, handle, key):
        """The sub-user behind an inbound reply, or an empty recordset."""
        key = (key or "").strip()
        if not key:
            return self.browse()
        domain = [("inbound_key", "!=", False)]
        if handle:
            domain.append(("handle", "=", str(handle).strip().lower()))
        for subuser in self.sudo().search(domain):
            if hmac.compare_digest(str(subuser.inbound_key), key):
                return subuser
        return self.browse()

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
            "reply": self.sudo()._reply_instructions(
                thread_model=record._name if record else False,
                thread_id=record.id if record else False,
            ),
        }
        result = self.dispatch(WEBHOOK_TYPE_PROMPT, payload, record=record)
        reply = (result.get("data") or {}).get("reply") if result.get("ok") else None
        if reply and self.post_reply and record:
            self._post_reply(record, reply)
        return result

    def _reply_instructions(self, chat_id=None, thread_model=None, thread_id=None):
        """How to answer this call, sent along with every prompt."""
        self.ensure_one()
        target = {}
        if chat_id:
            target["chat_id"] = chat_id
        if thread_model:
            target["thread_model"] = thread_model
            target["thread_id"] = thread_id
        return {
            "sync": "Answer this request with JSON {\"reply\": \"text\"} to post it immediately.",
            "async": {
                "url": "%s/promessaging/webhook/reply" % self.get_base_url(),
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": dict(
                    {
                        "subuser": self.handle,
                        "key": "<reply key from the sub-user settings>",
                        "message": "<your answer>",
                    },
                    **target
                ),
            },
        }

    @api.model
    def _split_message_and_plan(self, message):
        """Tell a written report apart from a plan sent in the message slot.

        Bots answer in both shapes, and a raw payload written onto a task as its
        note is unreadable, so pull the plan out and keep only real text.
        """
        if message is None:
            return None, None

        payload = message
        if isinstance(payload, str):
            text = payload.strip()
            if text[:1] not in "{[":
                return text[:500], None
            try:
                payload = json.loads(text)
            except ValueError:
                return text[:500], None

        if isinstance(payload, dict):
            plan = payload.get("plan")
            if plan is None and payload.get("steps"):
                plan = payload
            note = payload.get("message") or payload.get("note") or payload.get("text")
            note = note.strip()[:500] if isinstance(note, str) else None
            return note, plan
        if isinstance(payload, list):
            return None, {"steps": payload}
        return None, None

    def _receive_reply(self, message, chat_id=None, user_id=None, user_login=None,
                       thread_model=None, thread_id=None, draft_id=None,
                       objective_id=None, plan=None, summary_id=None, summary_values=None,
                       steps_done=None, steps_done_actor=None, document=None,
                       draft=None, subject=None):
        """Route an answer coming back from the AI to the right place."""
        self.ensure_one()
        subuser = self.sudo()

        # 1. a plan, or a report, on a daily summary task
        if objective_id:
            Objective = self.env.get("summaries.objective")
            if Objective is None:
                return {"ok": False, "error": "summaries_not_installed"}
            task = Objective.sudo().browse(int(objective_id)).exists()
            if not task:
                return {"ok": False, "error": "unknown_task"}
            note, plan_in_message = self._split_message_and_plan(message)
            if plan is None and plan_in_message is not None:
                plan = plan_in_message
            if plan is not None:
                task.set_plan(plan)
            if steps_done is not None or steps_done_actor:
                indexes = steps_done if isinstance(steps_done, (list, tuple)) else (
                    [steps_done] if steps_done is not None else []
                )
                task.mark_steps(indexes=indexes, done=True, actor=steps_done_actor)
            if document is not None:
                task.set_document(document)
            if note:
                task.sudo().note = note
            plan_now = task.get_plan()
            return {
                "ok": True,
                "target": "task",
                "objective_id": task.id,
                "summary_id": task.summary_id.id,
                # so the bot can see what it left for the person
                "task_done": plan_now["task_done"],
                "plan_state": plan_now["state"],
                "counts": plan_now["counts"],
            }

        # 2. a daily summary: an existing one by id, or a new one for a user
        if summary_id or summary_values:
            Summary = self.env.get("summaries.summary")
            if Summary is None:
                return {"ok": False, "error": "summaries_not_installed"}
            values = summary_values if isinstance(summary_values, dict) else {}

            if summary_id:
                summary = Summary.sudo().browse(int(summary_id)).exists()
                if not summary:
                    return {"ok": False, "error": "unknown_summary"}
                owner, day = summary.user_id.id, fields.Date.to_string(summary.date)
            else:
                owner = user_id or user_login
                if not owner:
                    return {"ok": False, "error": "missing_user"}
                day = values.get("date")

            try:
                created_id = Summary.sudo().upsert_summary(
                    owner,
                    day=day,
                    intro=values.get("intro"),
                    content=values.get("content"),
                    objectives=values.get("objectives"),
                )
            except UserError as error:
                return {"ok": False, "error": str(error)}

            summary = Summary.sudo().browse(created_id)
            return {
                "ok": True,
                "target": "summary",
                "summary_id": summary.id,
                "user_id": summary.user_id.id,
                "date": fields.Date.to_string(summary.date),
                # ids let a bot come back later to plan or report on a task
                "objectives": [
                    {"id": task.id, "name": task.name, "has_plan": task.has_plan}
                    for task in summary.objective_ids
                ],
            }

        # 3. a chatter draft: rewrite one by id, or write a new one on a document
        if draft_id or draft:
            Draft = self.env["promessaging.draft"].sudo()
            values = draft if isinstance(draft, dict) else {}
            body = values.get("body")
            if body is None:
                body = str(message) if message else None
            subject_line = values.get("subject", subject)

            if draft_id:
                record = Draft.browse(int(draft_id)).exists()
                if not record:
                    return {"ok": False, "error": "unknown_draft"}
                write_values = {"subuser_id": subuser.id}
                if body is not None:
                    write_values["body"] = body
                if subject_line is not None:
                    write_values["subject"] = (subject_line or "").strip()
                record.write(write_values)
            else:
                res_model = values.get("res_model") or values.get("thread_model")
                res_id = values.get("res_id") or values.get("thread_id")
                if not res_model or not res_id:
                    return {"ok": False, "error": "missing_document"}
                if body is None:
                    return {"ok": False, "error": "missing_body"}
                Draft.set_draft(res_model, int(res_id), body, subject=subject_line)
                record = Draft._find_draft(res_model, int(res_id))
                record.subuser_id = subuser.id

            return {
                "ok": True,
                "target": "draft",
                "draft_id": record.id,
                "res_model": record.res_model,
                "res_id": record.res_id,
                "subject": record.subject or "",
            }

        # 4. a direct conversation, by id or by who it is with
        chat = self.env["promessaging.ai.chat"].sudo()
        if chat_id:
            chat = chat.browse(int(chat_id)).exists()
            if not chat or chat.subuser_id != subuser:
                return {"ok": False, "error": "unknown_chat"}
        elif user_id or user_login:
            user = self.env["res.users"].sudo().browse(int(user_id)).exists() if user_id else (
                self.env["res.users"].sudo().search([("login", "=", user_login)], limit=1)
            )
            if not user:
                return {"ok": False, "error": "unknown_user"}
            chat = chat.search([
                ("user_id", "=", user.id), ("subuser_id", "=", subuser.id),
            ], limit=1) or chat.create({"user_id": user.id, "subuser_id": subuser.id})

        if chat:
            posted = chat._create_ai_message(message)
            return {
                "ok": True,
                "target": "chat",
                "chat_id": chat.id,
                "user_id": chat.user_id.id,
                "message_id": posted.id,
            }

        # 5. or a log note on the document the prompt came from
        if thread_model and thread_id:
            if thread_model not in self.env:
                return {"ok": False, "error": "unknown_model"}
            record = self.env[thread_model].sudo().browse(int(thread_id)).exists()
            if not record:
                return {"ok": False, "error": "unknown_document"}
            subuser._post_reply(record, message)
            return {
                "ok": True,
                "target": "chatter",
                "thread_model": thread_model,
                "thread_id": record.id,
            }

        return {"ok": False, "error": "no_target"}

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
