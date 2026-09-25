# -*- coding: utf-8 -*-
import base64
import json
from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install", "ba_upgrade_sync")
class TestUpgradeSyncExport(TransactionCase):
    """Quote created by user A, sent by A, confirmed by B, invoiced + posted by C:
    the export must list every step with the right user, from history only."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # capture off: the export must work from history alone (past dates)
        cls.env["ir.config_parameter"].sudo().set_param("ba_upgrade_sync.enabled", "False")
        groups = "sales_team.group_sale_salesman_all_leads,account.group_account_invoice"
        cls.user_a = new_test_user(cls.env, login="sync_exp_a", groups=groups)
        cls.user_b = new_test_user(cls.env, login="sync_exp_b", groups=groups)
        cls.user_c = new_test_user(cls.env, login="sync_exp_c", groups=groups)
        cls.product = cls.env["product.product"].create({
            "name": "Export Service", "type": "service", "list_price": 50.0, "invoice_policy": "order",
        })
        cls.partner = cls.env["res.partner"].create({"name": "Export Customer"})

    def _flush(self):
        self.env.flush_all()
        self.env.cr.precommit.run()   # mail tracking is written at pre-commit

    def _export(self, **vals):
        now = fields.Datetime.now()
        wizard = self.env["upgrade.sync.export.wizard"].create(dict({
            "date_from": now - timedelta(days=1),
            "date_to": now + timedelta(days=1),
            "source": "history",
        }, **vals))
        wizard.action_generate()
        return wizard, base64.b64decode(wizard.file_data)

    def test_history_lists_each_step_with_its_user(self):
        order = self.env["sale.order"].with_user(self.user_a).create({
            "partner_id": self.partner.id,
            "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 1})],
        })
        self._flush()
        order.with_user(self.user_a).action_quotation_sent()
        self._flush()
        order.with_user(self.user_b).action_confirm()
        self._flush()
        invoice = order.with_user(self.user_c)._create_invoices()
        self._flush()
        invoice.with_user(self.user_c).action_post()
        self._flush()

        wizard, raw = self._export()
        data = json.loads(raw)
        self.assertEqual(data["count"], len(data["actions"]))
        mine = [a for a in data["actions"]
                if (a["model"], a["record_id"]) in (("sale.order", order.id), ("account.move", invoice.id))]
        by_action = {a["action"]: a for a in mine}
        for action, user in [
            ("sale.create", self.user_a),
            ("sale.sent", self.user_a),
            ("sale.confirm", self.user_b),
            ("invoice.create_from_sale", self.user_c),
            ("invoice.post", self.user_c),
        ]:
            self.assertIn(action, by_action, "missing %s in %s" % (action, [a["action"] for a in mine]))
            self.assertEqual(by_action[action]["user_id"], user.id, action)
        self.assertEqual(by_action["invoice.create_from_sale"]["params"]["sale_order_ids"], [order.id])
        self.assertEqual(by_action["sale.confirm"]["related"]["partner_id"], self.partner.id)
        seqs = [a["sequence"] for a in data["actions"]]
        self.assertEqual(seqs, sorted(seqs))
        order_steps = [a["action"] for a in mine]
        self.assertLess(order_steps.index("sale.create"), order_steps.index("sale.confirm"))
        self.assertLess(order_steps.index("sale.confirm"), order_steps.index("invoice.post"))

    def test_csv_output_and_date_filter(self):
        self.env["res.partner"].create({"name": "Csv Partner"})
        self._flush()
        wizard, raw = self._export(output_format="csv")
        text = raw.decode("utf-8-sig")
        self.assertTrue(text.startswith("sequence,date,action,model,record_id"))
        self.assertIn("Csv Partner", text)
        # a window in the past contains none of today's actions
        now = fields.Datetime.now()
        wizard, raw = self._export(date_from=now - timedelta(days=30), date_to=now - timedelta(days=20))
        self.assertNotIn("Csv Partner", raw.decode())

    def test_captured_events_are_included(self):
        self.env["ir.config_parameter"].sudo().set_param("ba_upgrade_sync.enabled", "True")
        partner = self.env["res.partner"].create({"name": "Captured Partner"})
        self._flush()
        wizard, raw = self._export(source="capture")
        actions = json.loads(raw)["actions"]
        captured = [a for a in actions if a["record_id"] == partner.id and a["model"] == "res.partner"]
        self.assertTrue(captured)
        self.assertEqual(captured[0]["action"], "partner.upsert")
        self.assertTrue(captured[0]["event_uuid"])
