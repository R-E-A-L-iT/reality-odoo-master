# -*- coding: utf-8 -*-
import json
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install", "ba_upgrade_sync")
class TestUpgradeSyncCapture(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env["ir.config_parameter"].sudo().set_param("ba_upgrade_sync.enabled", "True")
        cls.env["ir.config_parameter"].sudo().set_param("ba_upgrade_sync.event_types", "")
        cls.Event = cls.env["upgrade.sync.event"]
        cls.product = cls.env["product.product"].create({
            "name": "Sync Test Service", "type": "service", "list_price": 100.0,
            "invoice_policy": "order",
        })

    def _flush(self):
        self.env.cr.precommit.run()

    def _events(self, since_id):
        return self.Event.search([("id", ">", since_id)], order="id")

    def _last_id(self):
        self._flush()
        return self.Event.search([], order="id desc", limit=1).id or 0

    def test_disabled_captures_nothing(self):
        self.env["ir.config_parameter"].sudo().set_param("ba_upgrade_sync.enabled", "False")
        start = self._last_id()
        self.env["res.partner"].create({"name": "No Capture"})
        self._flush()
        self.assertFalse(self._events(start))

    def test_partner_upsert_once_per_transaction(self):
        start = self._last_id()
        partner = self.env["res.partner"].create({"name": "ABC Ltd", "email": "abc@example.com"})
        partner.write({"phone": "123"})
        partner.write({"city": "Montreal"})
        self._flush()
        events = self._events(start).filtered(lambda e: e.model == "res.partner" and e.res_id == partner.id)
        self.assertEqual(events.mapped("event_type"), ["partner.upsert"])
        payload = json.loads(events.payload)
        self.assertEqual(payload["record"]["city"], "Montreal", "snapshot must hold the final state")
        self.assertEqual(payload["source"]["version"], "17.0")

    def test_sale_flow_events_in_order(self):
        start = self._last_id()
        partner = self.env["res.partner"].create({"name": "Flow Customer"})
        lead = self.env["crm.lead"].create({"name": "Flow Opp", "partner_id": partner.id, "type": "opportunity"})
        order = self.env["sale.order"].create({
            "partner_id": partner.id,
            "opportunity_id": lead.id,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 2})],
        })
        self._flush()
        order.action_quotation_sent()
        self._flush()
        order.action_confirm()
        self._flush()
        invoice = order._create_invoices()
        self._flush()
        invoice.action_post()
        self._flush()
        types = [
            e.event_type for e in self._events(start)
            if e.model in ("sale.order", "account.move")
        ]
        for expected in ("sale.upsert", "sale.sent", "sale.confirm", "invoice.create_from_sale", "invoice.post"):
            self.assertIn(expected, types)
        self.assertLess(types.index("sale.sent"), types.index("sale.confirm"))
        self.assertLess(types.index("sale.confirm"), types.index("invoice.create_from_sale"))
        self.assertLess(types.index("invoice.create_from_sale"), types.index("invoice.post"))
        create_ev = self._events(start).filtered(lambda e: e.event_type == "invoice.create_from_sale")
        self.assertEqual((create_ev.root_model, create_ev.root_id), ("sale.order", order.id))
        # the invoice built by _create_invoices must not also be an invoice.upsert
        # before its create_from_sale event
        self.assertNotIn("invoice.upsert", types[:types.index("invoice.create_from_sale")])

    def test_rollback_leaves_no_event(self):
        start = self._last_id()
        with self.assertRaises(RuntimeError):
            with self.env.cr.savepoint():
                self.env["res.partner"].create({"name": "Rolled back"})
                raise RuntimeError("abort")
        self._flush()
        self.assertFalse(self._events(start).filtered(lambda e: e.res_name == "Rolled back"))

    def test_capture_error_never_blocks_user(self):
        serializer = type(self.env["upgrade.sync.serializer"])
        with patch.object(serializer, "_snapshot", side_effect=ValueError("boom")):
            partner = self.env["res.partner"].create({"name": "Still Created"})
            self._flush()
        self.assertTrue(partner.exists())
