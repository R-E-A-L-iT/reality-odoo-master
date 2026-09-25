# -*- coding: utf-8 -*-
import base64
import json

from odoo.exceptions import UserError
from odoo.tests import tagged

from .test_upgrade_sync import UpgradeSyncCase


@tagged("post_install", "-at_install", "ba_upgrade_sync")
class TestUpgradeSyncImport(UpgradeSyncCase):
    """Import the Odoo 17 'Export User Actions' file: user A creates + sends a
    quote, user B confirms it, user C invoices and posts it."""

    def _file(self):
        partner_snap = self.partner_snap(760001, "Import Ltd", "import@example.com")
        partner = self.partner_ref(760001, "Import Ltd", "import@example.com")
        line = self.product_line(861001, qty=3, price=40.0)
        sale = self.sale_snap(860001, partner, [line], state="sale",
                              amount_untaxed=120.0, amount_tax=0.0, amount_total=120.0)
        invoice = {
            "model": "account.move", "id": 870001, "name": "INV/2026/09001", "move_type": "out_invoice",
            "state": "posted", "create_date": "2026-09-10T12:00:00", "partner_id": partner,
            "company_id": self.ref(self.company), "invoice_date": "2026-09-10",
            "sale_order_ids": [{"model": "sale.order", "id": 860001, "name": "S860001",
                                "create_date": "2026-09-21T10:00:00", "keys": {}}],
            "amount_untaxed": 120.0, "amount_tax": 0.0, "amount_total": 120.0,
            "lines": [{"id": 871001, "sequence": 10, "display_type": "product", "name": "Service",
                       "product_id": self.product_ref(), "quantity": 3.0, "price_unit": 40.0,
                       "discount": 0.0, "tax_ids": [],
                       "sale_line_ids": [{"model": "sale.order.line", "id": 861001, "name": "Service",
                                          "create_date": None, "keys": {}}]}],
        }

        def act(seq, date, action, model, rid, user, snap, **kw):
            return dict({"sequence": seq, "date": date, "action": action, "model": model,
                         "record_id": rid, "record_name": snap.get("name"), "user_id": user[0],
                         "user_login": user[1], "source": "history", "related": {},
                         "snapshot": snap}, **kw)

        a, b, c = (11, "usera@test.com"), (12, "userb@test.com"), (13, "userc@test.com")
        actions = [
            act(1, "2026-09-10 09:00:00", "partner.create", "res.partner", 760001, a, partner_snap),
            act(2, "2026-09-10 09:05:00", "sale.create", "sale.order", 860001, a, sale),
            act(3, "2026-09-10 09:10:00", "sale.sent", "sale.order", 860001, a, sale, message_id=5001),
            act(4, "2026-09-10 10:00:00", "sale.confirm", "sale.order", 860001, b, sale, message_id=5002),
            act(5, "2026-09-10 12:00:00", "invoice.create_from_sale", "account.move", 870001, c, invoice,
                params={"sale_order_ids": [860001]}, related={"sale_order_ids": [860001]}),
            act(6, "2026-09-10 12:05:00", "invoice.post", "account.move", 870001, c, invoice,
                message_id=5003, related={"sale_order_ids": [860001]}),
            act(7, "2026-09-10 12:06:00", "invoice.payment_state", "account.move", 870001, c, invoice,
                message_id=5004),
            {"sequence": 8, "date": "2026-09-10 12:07:00", "action": "sale.update", "model": "sale.order",
             "record_id": 860001, "user_id": 11, "source": "history"},          # no snapshot
        ]
        return {"database": "odoo17_test", "odoo_version": "17.0", "date_from": "2026-09-10 00:00:00",
                "date_to": "2026-09-11 00:00:00", "count": len(actions), "actions": actions}

    def _import(self, data, name="actions.json", **vals):
        raw = data if isinstance(data, bytes) else json.dumps(data).encode()
        wizard = self.env["upgrade.sync.import.wizard"].create(dict(
            {"file_data": base64.b64encode(raw), "file_name": name}, **vals))
        wizard.action_import()
        return wizard

    def test_import_recreates_client_example(self):
        wizard = self._import(self._file())
        self.assertEqual(wizard.imported_count, 6)
        self.assertEqual(wizard.skipped_count, 2, "payment_state (info) + line without snapshot")
        events = self.Event.search([("import_batch", "=", wizard.import_batch)])
        for event in events:
            self.assertEqual(event.state, "success", "%s: %s" % (event.event_type, event.error_message))
        self.assertEqual(set(events.mapped("origin")), {"import"})
        confirm = events.filtered(lambda e: e.event_type == "sale.confirm")
        self.assertEqual(confirm.source_user_login, "userb@test.com")

        order = self.target("sale.order", 860001)
        move = self.target("account.move", 870001)
        self.assertEqual(order.state, "sale")
        self.assertEqual(move.state, "posted")
        self.assertIn(order, move.invoice_line_ids.sale_line_ids.order_id)

    def test_same_file_twice_creates_nothing_new(self):
        first = self._import(self._file())
        orders_before = self.env["sale.order"].search_count([])
        second = self._import(self._file())
        self.assertEqual(second.imported_count, 0)
        self.assertEqual(second.duplicate_count, first.imported_count)
        self.assertEqual(self.env["sale.order"].search_count([]), orders_before)

    def test_captured_line_keeps_uuid_no_double_replay(self):
        data = self._file()
        snap = self.partner_snap(760002, "Captured Ltd", "captured@example.com")
        fetched, remote = self.make_event("partner.upsert", snap, seq=424242)
        data["actions"] = [{"sequence": 1, "date": "2026-09-12 08:00:00", "action": "partner.upsert",
                            "model": "res.partner", "record_id": 760002, "user_id": 2, "source": "capture",
                            "event_uuid": remote["name"], "event_id": 424242, "snapshot": snap}]
        wizard = self._import(data)
        self.assertEqual(wizard.imported_count, 0)
        self.assertEqual(wizard.duplicate_count, 1)

    def test_file_without_snapshots_is_refused(self):
        data = self._file()
        for line in data["actions"]:
            line.pop("snapshot", None)
        with self.assertRaises(UserError):
            self._import(data)

    def test_csv_file(self):
        data = self._file()
        header = ["sequence", "date", "action", "model", "record_id", "record_name", "user_id",
                  "user_login", "source", "related", "changes", "params", "event_uuid", "message_id", "snapshot"]
        import csv
        import io
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=header, extrasaction="ignore")
        writer.writeheader()
        for line in data["actions"][:4]:
            row = dict(line)
            for key in ("related", "changes", "params", "snapshot"):
                if key in row:
                    row[key] = json.dumps(row[key])
            writer.writerow(row)
        wizard = self._import(buffer.getvalue().encode("utf-8-sig"), name="actions.csv")
        self.assertEqual(wizard.imported_count, 4)
        self.assertEqual(self.target("sale.order", 860001).state, "sale")

    def test_dry_run_import_keeps_nothing(self):
        self.config.dry_run = True
        wizard = self._import(self._file())
        self.assertTrue(wizard.imported_count)
        self.assertFalse(self.target("sale.order", 860001))
