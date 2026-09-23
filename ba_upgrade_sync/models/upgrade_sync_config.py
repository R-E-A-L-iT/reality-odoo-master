# -*- coding: utf-8 -*-
import json
import logging
import os
import urllib.error
import urllib.request
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .exceptions import SyncRemoteError, SyncTransientError

_logger = logging.getLogger(__name__)

API_KEY_ENV = "UPGRADE_SYNC_API_KEY"
API_KEY_PARAM = "ba_upgrade_sync.api_key"
REMOTE_FIELDS = [
    "name", "event_type", "model", "res_id", "res_name", "root_model", "root_id",
    "user_login", "payload", "create_date",
]


class UpgradeSyncConfig(models.Model):
    _name = "upgrade.sync.config"
    _description = "Upgrade Sync Configuration"

    name = fields.Char(default="Odoo 17 source", required=True)
    source_url = fields.Char(
        "Odoo 17 URL", help="Base URL of the Odoo 17 instance, e.g. https://example.odoo.com")
    source_db = fields.Char("Odoo 17 database")
    source_login = fields.Char(
        "Technical user login",
        help="Odoo 17 user in the group 'Upgrade Sync Reader'. Its API key is read from the "
             "environment variable %s or set with 'Set API key' (stored as a system parameter, "
             "never displayed or logged)." % API_KEY_ENV)
    api_key_set = fields.Boolean(compute="_compute_api_key_set", string="API key configured")
    allow_insecure_http = fields.Boolean(
        help="Allow plain http:// (local development only). HTTPS is required otherwise.")
    timeout = fields.Integer("Timeout (s)", default=30)

    auto_sync = fields.Boolean(
        help="When enabled the scheduled action fetches and processes events automatically.")
    dry_run = fields.Boolean(
        default=True,
        help="Replay every event inside a savepoint that is always rolled back: validates "
             "mapping, transformation and business methods without changing Odoo 19 data.")
    batch_size = fields.Integer(default=100)
    max_attempts = fields.Integer(default=5)
    event_types = fields.Char(
        help="Comma-separated event types to replay (empty = all supported). Others are skipped.")
    snapshot_cutoff = fields.Datetime(
        help="When this Odoo 19 database was copied from Odoo 17. Odoo 17 records created before "
             "are matched on the same id when their fingerprint (creation date / name) agrees.")
    create_missing_partners = fields.Boolean(
        default=True,
        help="Create a minimal contact when an event references an Odoo 17 contact that has no "
             "counterpart and no pending event would create it.")
    overlap_minutes = fields.Integer(
        default=60,
        help="Events committed late in Odoo 17 (long transactions) are re-checked for this long.")

    last_cursor = fields.Integer("Last fetched Odoo 17 event id", default=0)
    last_fetch_date = fields.Datetime(readonly=True)
    last_fetch_message = fields.Text(readonly=True)

    # ------------------------------------------------------------------
    @api.model
    def _get_config(self):
        config = self.sudo().search([], limit=1)
        if not config:
            config = self.sudo().create({})
        return config

    def _get_api_key(self):
        return os.environ.get(API_KEY_ENV) or self.env["ir.config_parameter"].sudo().get_param(API_KEY_PARAM)

    def _compute_api_key_set(self):
        is_set = bool(self._get_api_key())
        for config in self:
            config.api_key_set = is_set

    def _replay_enabled(self, event_type):
        allowed = (self.event_types or "").strip()
        return not allowed or event_type in {t.strip() for t in allowed.split(",")}

    # ------------------------------------------------------------------
    # JSON-RPC client (Odoo 19 pulls from Odoo 17)
    # ------------------------------------------------------------------
    def _check_connection_settings(self):
        self.ensure_one()
        if not (self.source_url and self.source_db and self.source_login):
            raise UserError(_("Configure the Odoo 17 URL, database and login first."))
        if not self._get_api_key():
            raise UserError(_("No API key: set the %s environment variable or use 'Set API key'.", API_KEY_ENV))
        if not self.source_url.startswith("https://") and not self.allow_insecure_http:
            raise UserError(_("The Odoo 17 URL must use HTTPS."))

    def _jsonrpc(self, service, method, *args):
        self.ensure_one()
        body = json.dumps({
            "jsonrpc": "2.0", "method": "call", "id": 1,
            "params": {"service": service, "method": method, "args": list(args)},
        }).encode()
        request = urllib.request.Request(
            self.source_url.rstrip("/") + "/jsonrpc", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=self.timeout or 30) as response:
                answer = json.loads(response.read().decode())
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            # Never include the request body: it contains the API key.
            raise SyncTransientError("Odoo 17 unreachable: %s" % exc) from None
        if answer.get("error"):
            error = answer["error"]
            message = (error.get("data") or {}).get("message") or error.get("message")
            raise SyncRemoteError("Odoo 17 error: %s" % message)
        return answer.get("result")

    def _remote_execute(self, model, method, args, kwargs=None):
        self.ensure_one()
        key = self._get_api_key()
        uid = self._jsonrpc("common", "login", self.source_db, self.source_login, key)
        if not uid:
            raise SyncRemoteError("Odoo 17 authentication failed for login %s" % self.source_login)
        return self._jsonrpc("object", "execute_kw", self.source_db, uid, key, model, method, args, kwargs or {})

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def _fetch_events(self):
        """Pull new events from Odoo 17. Returns the number of events stored."""
        self.ensure_one()
        self._check_connection_settings()
        Event = self.env["upgrade.sync.event"].sudo()
        remote = self._remote_execute(
            "upgrade.sync.event", "search_read", [[("id", ">", self.last_cursor)]],
            {"fields": REMOTE_FIELDS, "order": "id asc", "limit": self.batch_size or 100})
        # Events committed late (long Odoo 17 transactions) can carry an id lower
        # than the cursor: re-check a recent window and fetch the ones we miss.
        since = fields.Datetime.to_string(fields.Datetime.now() - timedelta(minutes=self.overlap_minutes or 0))
        recent = self._remote_execute(
            "upgrade.sync.event", "search_read",
            [[("id", "<=", self.last_cursor), ("create_date", ">=", since)]],
            {"fields": ["name"], "order": "id asc"}) if self.last_cursor else []
        known = set(Event.search([("event_uuid", "in", [r["name"] for r in recent])]).mapped("event_uuid"))
        missing_ids = [r["id"] for r in recent if r["name"] not in known]
        if missing_ids:
            remote += self._remote_execute(
                "upgrade.sync.event", "read", [missing_ids], {"fields": REMOTE_FIELDS})
        stored = Event._store_remote_events(remote)
        cursor = max([r["id"] for r in remote] + [self.last_cursor])
        self.write({
            "last_cursor": cursor,
            "last_fetch_date": fields.Datetime.now(),
            "last_fetch_message": _("%(count)s new event(s), cursor at %(cursor)s.", count=stored, cursor=cursor),
        })
        return stored

    # ------------------------------------------------------------------
    # Buttons / cron
    # ------------------------------------------------------------------
    def action_fetch(self):
        self.ensure_one()
        try:
            count = self._fetch_events()
        except (SyncTransientError, SyncRemoteError) as exc:
            self.write({"last_fetch_date": fields.Datetime.now(), "last_fetch_message": str(exc)})
            raise UserError(str(exc)) from None
        return self._notify(_("%s new event(s) fetched.", count))

    def action_process(self):
        self.ensure_one()
        events = self.env["upgrade.sync.event"]._get_processable(self.batch_size or 100)
        events._process()
        return self._notify(_("%s event(s) processed.", len(events)))

    def action_test_connection(self):
        self.ensure_one()
        self._check_connection_settings()
        try:
            count = self._remote_execute("upgrade.sync.event", "search_count", [[]])
        except (SyncTransientError, SyncRemoteError) as exc:
            raise UserError(str(exc)) from None
        return self._notify(_("Connection OK: %s event(s) available in Odoo 17.", count))

    def action_set_api_key(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "upgrade.sync.api.key.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def _notify(self, message):
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "info", "sticky": False,
                       "next": {"type": "ir.actions.client", "tag": "soft_reload"}},
        }

    @api.model
    def _cron_sync(self):
        config = self._get_config()
        if not config.auto_sync:
            return
        try:
            config._fetch_events()
        except (SyncTransientError, SyncRemoteError, UserError) as exc:
            _logger.warning("Upgrade sync: fetch failed: %s", exc)
            config.write({"last_fetch_date": fields.Datetime.now(), "last_fetch_message": str(exc)})
        self.env["ir.cron"]._commit_progress()
        events = self.env["upgrade.sync.event"]._get_processable(config.batch_size or 100)
        events._process(commit=True)


class UpgradeSyncApiKeyWizard(models.TransientModel):
    _name = "upgrade.sync.api.key.wizard"
    _description = "Set the Odoo 17 API key"

    api_key = fields.Char(required=True)

    def action_save(self):
        self.ensure_one()
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only administrators can set the API key."))
        self.env["ir.config_parameter"].sudo().set_param(API_KEY_PARAM, self.api_key)
        # do not keep the secret in the transient table
        self.api_key = "********"
        return {"type": "ir.actions.act_window_close"}
