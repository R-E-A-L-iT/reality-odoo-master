# -*- coding: utf-8 -*-
import json
import logging
import traceback
from datetime import timedelta

from psycopg2 import OperationalError

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError, ValidationError

from .exceptions import SyncDependencyMissing, SyncError, SyncTransientError

_logger = logging.getLogger(__name__)

DONE_STATES = ("success", "skipped", "dry_run_ok")
# minutes to wait before attempt n+1
BACKOFF_MINUTES = [5, 15, 60, 240, 720]


class _DryRunRollback(Exception):
    """Raised at the end of a dry-run replay to roll the savepoint back."""

    def __init__(self, target, comparison):
        super().__init__("dry run")
        self.target = target
        self.comparison = comparison


class UpgradeSyncEvent(models.Model):
    _name = "upgrade.sync.event"
    _description = "Upgrade Sync Event (replayed in Odoo 19)"
    _order = "source_sequence desc, id desc"
    _rec_name = "event_uuid"

    event_uuid = fields.Char("Event ID", required=True, readonly=True, index=True, copy=False)
    source_sequence = fields.Integer("Odoo 17 Seq", readonly=True, index=True,
                                     help="Id of the event in Odoo 17: the replay order.")
    event_type = fields.Char(required=True, readonly=True, index=True)
    source_model = fields.Char("Model", readonly=True, index=True)
    source_res_id = fields.Integer("Odoo 17 ID", readonly=True, index=True)
    source_res_name = fields.Char("Odoo 17 Record", readonly=True)
    root_key = fields.Char(readonly=True, index=True,
                           help="Business document the event belongs to (e.g. sale.order,42). "
                                "Events of the same document are replayed strictly in order.")
    source_user_login = fields.Char("Odoo 17 User", readonly=True)
    source_date = fields.Datetime("Date", readonly=True, index=True)
    payload = fields.Text(readonly=True)

    state = fields.Selection([
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("waiting", "Waiting"),
        ("success", "Success"),
        ("dry_run_ok", "Dry Run OK"),
        ("failed", "Failed"),
        ("skipped", "Skipped"),
    ], default="pending", required=True, index=True)
    error_kind = fields.Selection([
        ("dependency", "Missing dependency"),
        ("master_data", "Missing master data"),
        ("business", "Business / validation error"),
        ("transient", "Network / availability"),
        ("technical", "Technical error"),
    ], readonly=True)
    error_message = fields.Text(readonly=True)
    attempt_count = fields.Integer("Attempts", readonly=True)
    last_attempt = fields.Datetime(readonly=True)
    next_retry = fields.Datetime(readonly=True, index=True)
    processed_at = fields.Datetime(readonly=True)

    target_model = fields.Char(readonly=True)
    target_res_id = fields.Integer("Odoo 19 ID", readonly=True)
    target_display = fields.Char("Odoo 19 Record", readonly=True)
    comparison_result = fields.Selection([
        ("match", "Match"),
        ("mismatch", "Mismatch"),
        ("na", "N/A"),
    ], readonly=True, index=True)
    comparison_html = fields.Html(readonly=True, sanitize=True)

    _event_uuid_uniq = models.Constraint("unique(event_uuid)", "This event has already been received.")

    # ------------------------------------------------------------------
    # Reception
    # ------------------------------------------------------------------
    @api.model
    def _store_remote_events(self, remote_events):
        """Store events read from Odoo 17. Duplicates (same UUID) are ignored."""
        uuids = [r["name"] for r in remote_events]
        known = set(self.search([("event_uuid", "in", uuids)]).mapped("event_uuid"))
        vals_list = []
        for r in remote_events:
            if r["name"] in known:
                continue
            known.add(r["name"])
            vals_list.append(self._prepare_event_vals(r))
        self.create(vals_list)
        return len(vals_list)

    @api.model
    def _prepare_event_vals(self, r):
        try:
            json.loads(r.get("payload") or "{}")
        except ValueError:
            raise ValidationError(_("Event %s has an invalid JSON payload.", r["name"])) from None
        root_model = r.get("root_model") or r["model"]
        root_id = r.get("root_id") or r["res_id"]
        return {
            "event_uuid": r["name"],
            "source_sequence": r["id"],
            "event_type": r["event_type"],
            "source_model": r["model"],
            "source_res_id": r["res_id"],
            "source_res_name": r.get("res_name"),
            "root_key": "%s,%s" % (root_model, root_id),
            "source_user_login": r.get("user_login"),
            "source_date": r.get("create_date"),
            "payload": r.get("payload"),
        }

    def _get_payload(self):
        self.ensure_one()
        return json.loads(self.payload or "{}")

    # ------------------------------------------------------------------
    # Processing
    # ------------------------------------------------------------------
    @api.model
    def _get_processable(self, limit):
        now = fields.Datetime.now()
        return self.search([
            ("state", "in", ("pending", "waiting")),
            "|", ("next_retry", "=", False), ("next_retry", "<=", now),
        ], order="source_sequence asc, id asc", limit=limit)

    def _process(self, commit=False):
        config = self.env["upgrade.sync.config"]._get_config()
        for event in self.sorted(lambda e: (e.source_sequence, e.id)):
            event._process_one(config)
            if commit:
                self.env["ir.cron"]._commit_progress(1)

    def _blocking_event(self):
        """Earlier, unfinished event of the same business document."""
        self.ensure_one()
        return self.search([
            ("root_key", "=", self.root_key),
            ("source_sequence", "<", self.source_sequence),
            ("state", "not in", DONE_STATES),
            ("id", "!=", self.id),
        ], order="source_sequence asc", limit=1)

    def _pending_event_for(self, ref):
        """Unfinished event that would create/update the referenced record."""
        if not ref:
            return self.browse()
        return self.search([
            ("source_model", "=", ref.get("model")),
            ("source_res_id", "=", ref.get("id")),
            ("state", "not in", DONE_STATES),
            ("id", "!=", self.id),
        ], order="source_sequence asc", limit=1)

    def _process_one(self, config):
        self.ensure_one()
        now = fields.Datetime.now()
        if self.state in DONE_STATES:
            return
        blocker = self._blocking_event()
        if blocker:
            self.write({
                "state": "waiting",
                "error_kind": "dependency",
                "error_message": _("Waiting for earlier event %(uuid)s (%(type)s, %(state)s) of the same document.",
                                   uuid=blocker.event_uuid, type=blocker.event_type, state=blocker.state),
                "next_retry": now + timedelta(minutes=1),
            })
            return
        handler = self.env["upgrade.sync.handler"]
        if not config._replay_enabled(self.event_type) or not handler._get_handler_method(self.event_type):
            self.write({"state": "skipped", "processed_at": now,
                        "error_message": _("Event type %s is disabled or has no handler.", self.event_type)})
            return

        self.write({"state": "processing", "attempt_count": self.attempt_count + 1, "last_attempt": now})
        payload = self._get_payload()
        try:
            with self.env.cr.savepoint():
                target = handler._dispatch(self, payload)
                comparison = self.env["upgrade.sync.comparator"]._compare(self, payload, target)
                if config.dry_run:
                    raise _DryRunRollback(target and (target._name, target.id, target.display_name), comparison)
            self._mark_success(target and (target._name, target.id, target.display_name), comparison)
        except _DryRunRollback as dry:
            self.env.invalidate_all()
            self._mark_success(dry.target, dry.comparison, state="dry_run_ok")
        except SyncDependencyMissing as exc:
            self.env.invalidate_all()
            self._on_dependency_missing(exc, config)
        except SyncTransientError as exc:
            self.env.invalidate_all()
            self._mark_retry_or_fail(exc.kind, str(exc), config)
        except OperationalError as exc:
            self.env.invalidate_all()
            self._mark_retry_or_fail("transient", str(exc), config)
        except (SyncError, UserError, ValidationError, AccessError) as exc:
            self.env.invalidate_all()
            kind = getattr(exc, "kind", "business")
            self._mark_failed(kind, str(exc))
        except Exception as exc:  # pylint: disable=broad-except
            self.env.invalidate_all()
            _logger.exception("Upgrade sync: event %s failed", self.event_uuid)
            self._mark_failed("technical", "%s\n\n%s" % (exc, traceback.format_exc(limit=8)))

    def _mark_success(self, target, comparison, state="success"):
        result, html = comparison or ("na", False)
        vals = {
            "state": state,
            "processed_at": fields.Datetime.now(),
            "error_kind": False,
            "error_message": False,
            "next_retry": False,
            "comparison_result": result,
            "comparison_html": html,
        }
        if target:
            vals.update({"target_model": target[0], "target_res_id": target[1], "target_display": target[2]})
        self.write(vals)

    def _mark_failed(self, kind, message):
        self.write({"state": "failed", "error_kind": kind, "error_message": message, "next_retry": False})

    def _mark_retry_or_fail(self, kind, message, config):
        if self.attempt_count >= (config.max_attempts or 1):
            self._mark_failed(kind, _("%(msg)s\n(gave up after %(n)s attempts)", msg=message, n=self.attempt_count))
            return
        delay = BACKOFF_MINUTES[min(self.attempt_count - 1, len(BACKOFF_MINUTES) - 1)]
        self.write({
            "state": "waiting",
            "error_kind": kind,
            "error_message": message,
            "next_retry": fields.Datetime.now() + timedelta(minutes=delay),
        })

    def _on_dependency_missing(self, exc, config):
        if config.dry_run and exc.ref:
            simulated = self.search([
                ("source_model", "=", exc.ref.get("model")),
                ("source_res_id", "=", exc.ref.get("id")),
                ("state", "=", "dry_run_ok"),
            ], limit=1)
            if simulated:
                # Nothing is kept in dry run, so a document "created" by an
                # earlier event does not exist: this event cannot go further.
                self._mark_success(None, ("na", False), state="dry_run_ok")
                self.error_message = _("Dry run: depends on %s, which was only simulated.", simulated.event_uuid)
                return
        pending = self._pending_event_for(exc.ref)
        if pending:
            # Do not burn an attempt while the dependency is simply queued.
            self.write({
                "state": "waiting",
                "attempt_count": self.attempt_count - 1,
                "error_kind": "dependency",
                "error_message": _("%(msg)s. Waiting for event %(uuid)s.", msg=str(exc), uuid=pending.event_uuid),
                "next_retry": fields.Datetime.now() + timedelta(minutes=2),
            })
            return
        self._mark_retry_or_fail("dependency", str(exc), config)

    # ------------------------------------------------------------------
    # Admin actions
    # ------------------------------------------------------------------
    def action_retry(self):
        """Reset to pending: the event is replayed at the next processing run."""
        self.filtered(lambda e: e.state not in ("success", "processing")).write({
            "state": "pending", "attempt_count": 0, "next_retry": False,
            "error_kind": False, "error_message": False,
        })

    def action_process_now(self):
        config = self.env["upgrade.sync.config"]._get_config()
        todo = self.filtered(lambda e: e.state in ("pending", "waiting", "failed"))
        todo.filtered(lambda e: e.state == "failed").action_retry()
        for event in todo.sorted(lambda e: (e.source_sequence, e.id)):
            event._process_one(config)

    def action_replay(self):
        """Replay an already successful event again (idempotent handlers)."""
        self.write({"state": "pending", "attempt_count": 0, "next_retry": False,
                    "error_kind": False, "error_message": False})

    def action_skip(self):
        self.filtered(lambda e: e.state != "success").write({
            "state": "skipped", "processed_at": fields.Datetime.now()})

    def action_open_target(self):
        self.ensure_one()
        if not (self.target_model and self.target_res_id):
            raise UserError(_("This event has no Odoo 19 record."))
        return {
            "type": "ir.actions.act_window",
            "res_model": self.target_model,
            "res_id": self.target_res_id,
            "view_mode": "form",
            "target": "current",
        }
