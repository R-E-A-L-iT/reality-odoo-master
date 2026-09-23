# -*- coding: utf-8 -*-
"""Odoo 17 capture side of the upgrade sync.

Business code calls ``env['upgrade.sync.event']._enqueue(...)``. The request is
stored on the cursor's pre-commit data and turned into ``upgrade.sync.event``
rows right before the transaction commits, so:

* several writes on the same record in one transaction produce one upsert event
  whose snapshot is the final state of the record;
* a rolled-back transaction (or savepoint) leaves no event behind;
* the user never waits for Odoo 19: nothing leaves this database, the Odoo 19
  instance pulls the events later.
"""
import json
import logging
import uuid
from functools import partial

from odoo import SUPERUSER_ID, api, fields, models

_logger = logging.getLogger(__name__)

QUEUE_KEY = "ba_upgrade_sync.queue"
PARAM_ENABLED = "ba_upgrade_sync.enabled"
PARAM_EVENT_TYPES = "ba_upgrade_sync.event_types"
PAYLOAD_SCHEMA = 1

# Event type -> short description. Keep in sync with the Odoo 19 receiver.
EVENT_TYPES = [
    ("partner.upsert", "Customer created/updated"),
    ("product.upsert", "Product created/updated"),
    ("lead.upsert", "Opportunity created/updated"),
    ("lead.stage", "Opportunity stage changed"),
    ("lead.won", "Opportunity won"),
    ("lead.lost", "Opportunity lost"),
    ("sale.upsert", "Quotation created/updated"),
    ("sale.sent", "Quotation sent"),
    ("sale.confirm", "Sales order confirmed"),
    ("sale.cancel", "Sales order cancelled"),
    ("sale.draft", "Sales order reset to quotation"),
    ("invoice.create_from_sale", "Invoice created from sales order"),
    ("invoice.upsert", "Invoice created/updated"),
    ("invoice.post", "Invoice posted"),
    ("invoice.cancel", "Invoice cancelled"),
    ("invoice.draft", "Invoice reset to draft"),
    ("invoice.reverse", "Credit note created (reversal)"),
]


def _flush_queue(cr):
    """Pre-commit callback: build snapshots and store the queued events."""
    queue = cr.precommit.data.pop(QUEUE_KEY, None)
    if not queue:
        return
    env = api.Environment(cr, SUPERUSER_ID, {"upgrade_sync_skip": True, "active_test": False})
    env["upgrade.sync.event"]._store_queue(queue)


class UpgradeSyncEvent(models.Model):
    _name = "upgrade.sync.event"
    _description = "Upgrade Sync Event (captured in Odoo 17)"
    _order = "id desc"
    _rec_name = "name"

    name = fields.Char("Event UUID", required=True, readonly=True, index=True, copy=False)
    event_type = fields.Selection(EVENT_TYPES, required=True, readonly=True, index=True)
    model = fields.Char(required=True, readonly=True, index=True)
    res_id = fields.Integer("Record ID", required=True, readonly=True, index=True)
    res_name = fields.Char("Record", readonly=True)
    root_model = fields.Char(readonly=True, help="Ordering group, e.g. the sales order of an invoice.")
    root_id = fields.Integer(readonly=True)
    user_id = fields.Many2one("res.users", "Done by", readonly=True)
    user_login = fields.Char(readonly=True)
    company_id = fields.Many2one("res.company", readonly=True)
    payload = fields.Text(readonly=True, help="JSON business snapshot.")
    capture_error = fields.Text(readonly=True)

    _sql_constraints = [
        ("name_uniq", "unique(name)", "The event UUID must be unique."),
    ]

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @api.model
    def _capture_enabled(self, event_type):
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param(PARAM_ENABLED) not in ("True", "true", "1"):
            return False
        allowed = (ICP.get_param(PARAM_EVENT_TYPES) or "").strip()
        if not allowed:
            return True
        return event_type in {t.strip() for t in allowed.split(",")}

    # ------------------------------------------------------------------
    # Capture API used by the model overrides
    # ------------------------------------------------------------------
    @api.model
    def _enqueue(self, event_type, records, root=None, extra=None):
        """Queue ``event_type`` for each record of ``records``.

        Never raises: a capture problem must not break the user's action.

        :param root: callable(record) -> record used as ordering group
                     (defaults to the record itself)
        :param extra: dict or callable(record) -> dict of action parameters
        """
        if not records or self.env.context.get("upgrade_sync_skip"):
            return
        try:
            if not self._capture_enabled(event_type):
                return
            cr = self.env.cr
            queue = cr.precommit.data.get(QUEUE_KEY)
            if queue is None:
                queue = cr.precommit.data[QUEUE_KEY] = []
                cr.precommit.add(partial(_flush_queue, cr))
            is_upsert = event_type.endswith(".upsert")
            for record in records:
                if is_upsert and any(
                    q["event_type"] == event_type and q["model"] == record._name and q["res_id"] == record.id
                    for q in queue
                ):
                    # One upsert per record and transaction: the snapshot is taken
                    # at commit time, so it already holds the final state.
                    continue
                root_rec = root(record) if root else record
                queue.append({
                    "event_type": event_type,
                    "model": record._name,
                    "res_id": record.id,
                    "root_model": root_rec._name if root_rec else record._name,
                    "root_id": root_rec.id if root_rec else record.id,
                    "uid": self.env.uid,
                    "extra": (extra(record) if callable(extra) else extra) or {},
                })
        except Exception:  # pylint: disable=broad-except
            _logger.exception("Upgrade sync: could not queue %s for %s", event_type, records)

    @api.model
    def _store_queue(self, queue):
        serializer = self.env["upgrade.sync.serializer"]
        for item in queue:
            try:
                with self.env.cr.savepoint(flush=False):
                    record = self.env[item["model"]].browse(item["res_id"]).exists()
                    if not record:
                        continue
                    user = self.env["res.users"].browse(item["uid"]).exists()
                    payload = {
                        "schema": PAYLOAD_SCHEMA,
                        "source": {"db": self.env.cr.dbname, "version": "17.0"},
                        "record": serializer._snapshot(record),
                        "extra": item["extra"],
                    }
                    self.create({
                        "name": str(uuid.uuid4()),
                        "event_type": item["event_type"],
                        "model": item["model"],
                        "res_id": item["res_id"],
                        "res_name": record.display_name,
                        "root_model": item["root_model"],
                        "root_id": item["root_id"],
                        "user_id": user.id,
                        "user_login": user.login,
                        "company_id": record.company_id.id if "company_id" in record._fields else False,
                        "payload": json.dumps(payload, default=str),
                    })
                    self.flush_model()
            except Exception:  # pylint: disable=broad-except
                _logger.exception("Upgrade sync: could not store event %s", item.get("event_type"))

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def action_open_record(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }
