# -*- coding: utf-8 -*-
import itertools
import json
import uuid
from unittest.mock import patch

from odoo.tests import TransactionCase, tagged

from ..models.exceptions import SyncTransientError

_seq = itertools.count(1000)


@tagged("post_install", "-at_install", "ba_upgrade_sync")
class UpgradeSyncCase(TransactionCase):
    """Builds Odoo 17-shaped events (same format as the Odoo 17 serializer)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.config = cls.env["upgrade.sync.config"]._get_config()
        cls.config.write({"dry_run": False, "auto_sync": False, "max_attempts": 3,
                          "event_types": False, "snapshot_cutoff": False})
        cls.Event = cls.env["upgrade.sync.event"]
        cls.Mapping = cls.env["upgrade.sync.mapping"]
        cls.company = cls.env.company
        cls.uom_unit = cls.env.ref("uom.product_uom_unit")
        cls.product = cls.env["product.product"].create({
            "name": "Upgrade Sync Service", "type": "service", "list_price": 100.0,
            "invoice_policy": "order", "taxes_id": [(6, 0, [])],
        })
        # Odoo 17 ids deliberately different from the Odoo 19 ones
        cls.src_product_id = 900001
        cls.Mapping._set("product.product", cls.src_product_id, cls.product, "manual")

    # -- Odoo 17 shaped helpers -------------------------------------------
    @classmethod
    def ref(cls, record, source_id=None, **keys):
        return {
            "model": record._name,
            "id": source_id or record.id,
            "name": record.display_name,
            "create_date": record.create_date and record.create_date.isoformat(),
            "keys": dict({"name": record.display_name}, **keys),
        }

    def product_ref(self):
        return {"model": "product.product", "id": self.src_product_id, "name": self.product.name,
                "create_date": None, "keys": {"default_code": None, "name": self.product.name}}

    def partner_snap(self, src_id, name, email):
        return {
            "model": "res.partner", "id": src_id, "name": name, "is_company": True,
            "create_date": "2026-09-20T10:00:00", "email": email, "type": "contact",
            "company_id": None, "parent_id": None, "active": True,
        }

    def partner_ref(self, src_id, name, email):
        return {"model": "res.partner", "id": src_id, "name": name, "create_date": "2026-09-20T10:00:00",
                "keys": {"email": email, "is_company": True, "name": name}}

    def sale_snap(self, src_id, partner_ref, lines, state="draft", **extra):
        snap = {
            "model": "sale.order", "id": src_id, "name": "S%05d" % src_id, "state": state,
            "create_date": "2026-09-21T10:00:00",
            "partner_id": partner_ref, "partner_invoice_id": partner_ref, "partner_shipping_id": partner_ref,
            "company_id": self.ref(self.company), "date_order": "2026-09-21T10:00:00",
            "amount_untaxed": 0.0, "amount_tax": 0.0, "amount_total": 0.0, "lines": lines,
        }
        snap.update(extra)
        return snap

    def product_line(self, src_id, qty=2.0, price=100.0, seq=10, **extra):
        line = {
            "id": src_id, "sequence": seq, "display_type": False, "name": "Service",
            "product_id": self.product_ref(), "product_uom_qty": qty,
            "product_uom": self.ref(self.uom_unit), "tax_id": [], "price_unit": price, "discount": 0.0,
            "selected": "true", "sectionSelected": "true", "special": "regular", "optional": "no",
        }
        line.update(extra)
        return line

    def make_event(self, event_type, snap, root=None, extra=None, seq=None):
        root_model, root_id = root or (snap["model"], snap["id"])
        remote = {
            "id": seq or next(_seq), "name": str(uuid.uuid4()), "event_type": event_type,
            "model": snap["model"], "res_id": snap["id"], "res_name": snap.get("name"),
            "root_model": root_model, "root_id": root_id, "user_login": "admin",
            "create_date": "2026-09-22 10:00:00",
            "payload": json.dumps({"schema": 1, "source": {"db": "odoo17", "version": "17.0"},
                                   "record": snap, "extra": extra or {}}),
        }
        self.Event._store_remote_events([remote])
        return self.Event.search([("event_uuid", "=", remote["name"])]), remote

    def target(self, model, src_id):
        return self.Mapping._lookup(model, src_id)


class TestUpgradeSync(UpgradeSyncCase):

    def test_duplicate_event_received_once(self):
        snap = self.partner_snap(700001, "Dup Ltd", "dup@example.com")
        event, remote = self.make_event("partner.upsert", snap)
        self.Event._store_remote_events([remote])
        self.assertEqual(self.Event.search_count([("event_uuid", "=", remote["name"])]), 1)

    def test_idempotent_replay(self):
        partner = self.partner_ref(700002, "Idem Ltd", "idem@example.com")
        self.make_event("partner.upsert", self.partner_snap(700002, "Idem Ltd", "idem@example.com"))[0] \
            .action_process_now()
        snap = self.sale_snap(800001, partner, [self.product_line(810001)])
        event, _r = self.make_event("sale.upsert", snap)
        event.action_process_now()
        self.assertEqual(event.state, "success", event.error_message)
        order = self.target("sale.order", 800001)
        event.action_replay()
        event.action_process_now()
        self.assertEqual(event.state, "success", event.error_message)
        self.assertEqual(self.target("sale.order", 800001), order)
        self.assertEqual(self.env["sale.order"].search_count([("partner_id", "=", order.partner_id.id)]), 1)
        self.assertEqual(len(order.order_line), 1)

    def test_seed_mapping_by_fingerprint(self):
        existing = self.env["res.partner"].create({"name": "Seeded Co", "email": "seed@example.com"})
        ref = self.ref(existing)                       # same id + same create_date
        self.assertEqual(self.env["upgrade.sync.resolver"]._resolve(ref), existing)
        mapping = self.Mapping.search([("source_model", "=", "res.partner"), ("source_id", "=", existing.id)])
        self.assertEqual(mapping.match_method, "seed_id")

    def test_same_id_different_record_not_seeded(self):
        other = self.env["res.partner"].create({"name": "Somebody Else"})
        ref = {"model": "res.partner", "id": other.id, "name": "Totally Different",
               "create_date": "2001-01-01T00:00:00", "keys": {"email": "diff@example.com", "is_company": False}}
        self.config.create_missing_partners = False
        resolved = self.env["upgrade.sync.resolver"]._resolve(ref, required=False)
        self.assertFalse(resolved)

    def test_missing_master_data_fails_without_creating(self):
        partner = self.partner_ref(700003, "Tax Ltd", "tax@example.com")
        self.make_event("partner.upsert", self.partner_snap(700003, "Tax Ltd", "tax@example.com"))[0] \
            .action_process_now()
        bad_tax = {"model": "account.tax", "id": 999999, "name": "No Such Tax", "create_date": None,
                   "keys": {"name": "No Such Tax", "amount": 13.0, "type_tax_use": "sale", "company": "Nope"}}
        line = self.product_line(810002, tax_id=[bad_tax])
        event, _r = self.make_event("sale.upsert", self.sale_snap(800002, partner, [line]))
        taxes_before = self.env["account.tax"].search_count([])
        event.action_process_now()
        self.assertEqual(event.state, "failed")
        self.assertEqual(event.error_kind, "master_data")
        self.assertEqual(self.env["account.tax"].search_count([]), taxes_before)
        self.assertFalse(self.target("sale.order", 800002))

    def test_same_document_events_in_order(self):
        partner = self.partner_ref(700004, "Order Ltd", "order@example.com")
        self.make_event("partner.upsert", self.partner_snap(700004, "Order Ltd", "order@example.com"))[0] \
            .action_process_now()
        snap = self.sale_snap(800003, partner, [self.product_line(810003)])
        upsert, _r = self.make_event("sale.upsert", snap, seq=50001)
        confirm, _r = self.make_event("sale.confirm", dict(snap, state="sale"), seq=50002)
        confirm.action_process_now()          # earlier event not replayed yet
        self.assertEqual(confirm.state, "waiting")
        self.assertIn(upsert.event_uuid, confirm.error_message)
        (upsert | confirm).action_process_now()
        self.assertEqual(upsert.state, "success", upsert.error_message)
        self.assertEqual(confirm.state, "success", confirm.error_message)
        self.assertEqual(self.target("sale.order", 800003).state, "sale")

    def test_missing_dependency_waits_for_queued_event(self):
        partner = self.partner_ref(700005, "Later Ltd", "later@example.com")
        self.config.create_missing_partners = False
        partner_event, _r = self.make_event(
            "partner.upsert", self.partner_snap(700005, "Later Ltd", "later@example.com"), seq=60002)
        sale_event, _r = self.make_event(
            "sale.upsert", self.sale_snap(800004, partner, [self.product_line(810004)]), seq=60001)
        sale_event.action_process_now()
        self.assertEqual(sale_event.state, "waiting")
        self.assertEqual(sale_event.error_kind, "dependency")
        self.assertEqual(sale_event.attempt_count, 0, "a queued dependency must not burn attempts")
        partner_event.action_process_now()
        sale_event.action_process_now()
        self.assertEqual(sale_event.state, "success", sale_event.error_message)

    def test_optional_section_transformation(self):
        partner = self.partner_ref(700006, "Opt Ltd", "opt@example.com")
        self.make_event("partner.upsert", self.partner_snap(700006, "Opt Ltd", "opt@example.com"))[0] \
            .action_process_now()
        lines = [
            self.product_line(810010, qty=1, seq=1),
            {"id": 810011, "sequence": 2, "display_type": "line_section", "name": "Options",
             "special": "optional", "selected": "true", "sectionSelected": "true"},
            self.product_line(810012, qty=3, seq=3, selected="false", optional="yes"),
            self.product_line(810013, qty=2, seq=4, selected="true", optional="yes"),
        ]
        event, _r = self.make_event("sale.upsert", self.sale_snap(800005, partner, lines))
        event.action_process_now()
        self.assertEqual(event.state, "success", event.error_message)
        section = self.target("sale.order.line", 810011)
        unselected = self.target("sale.order.line", 810012)
        selected = self.target("sale.order.line", 810013)
        self.assertTrue(section.is_optional)
        self.assertEqual(unselected.x_optional_section_id, section)
        self.assertEqual(unselected.product_uom_qty, 0.0, "Odoo 17 unselected line -> qty 0 in Odoo 19")
        self.assertEqual(unselected.x_preset_qty, 3.0, "Odoo 17 qty kept as preset")
        self.assertEqual(selected.product_uom_qty, 2.0)
        self.assertEqual(self.target("sale.order.line", 810010).product_uom_qty, 1.0)

    def test_product_type_transformation(self):
        snap = {"model": "product.template", "id": 910001, "name": "Storable Widget",
                "create_date": "2026-09-22T09:00:00", "detailed_type": "product", "type": "product",
                "default_code": "UPG-WIDGET-1", "list_price": 10.0, "standard_price": 5.0,
                "sale_ok": True, "purchase_ok": True, "invoice_policy": "order",
                "categ_id": self.ref(self.env.ref("product.product_category_all"),
                                     complete_name=self.env.ref("product.product_category_all").complete_name),
                "uom_id": self.ref(self.uom_unit), "taxes_id": [], "supplier_taxes_id": [],
                "company_id": None, "active": True, "variants": []}
        event, _r = self.make_event("product.upsert", snap)
        event.action_process_now()
        self.assertEqual(event.state, "success", event.error_message)
        template = self.target("product.template", 910001)
        self.assertEqual(template.type, "consu")
        self.assertTrue(template.is_storable, "Odoo 17 'product' type -> Odoo 19 consu + is_storable")

    def test_dry_run_changes_nothing(self):
        self.config.dry_run = True
        snap = self.partner_snap(700007, "Dry Ltd", "dry@example.com")
        event, _r = self.make_event("partner.upsert", snap)
        event.action_process_now()
        self.assertEqual(event.state, "dry_run_ok", event.error_message)
        self.assertFalse(self.env["res.partner"].search([("email", "=", "dry@example.com")]))
        self.assertFalse(self.target("res.partner", 700007))

    def test_transient_error_retries_then_fails(self):
        event, _r = self.make_event("partner.upsert", self.partner_snap(700008, "Net Ltd", "net@example.com"))
        handler_cls = type(self.env["upgrade.sync.handler"])
        with patch.object(handler_cls, "_dispatch", side_effect=SyncTransientError("Odoo 17 unreachable")):
            event.action_process_now()
            self.assertEqual(event.state, "waiting")
            self.assertEqual(event.attempt_count, 1)
            self.assertTrue(event.next_retry)
            for _i in range(5):
                if event.state != "waiting":
                    break
                event.next_retry = False
                event.action_process_now()
        self.assertEqual(event.state, "failed")
        self.assertEqual(event.attempt_count, self.config.max_attempts)

    def test_fetch_failure_keeps_cursor(self):
        self.config.write({"source_url": "https://odoo17.invalid", "source_db": "db", "source_login": "sync"})
        self.env["ir.config_parameter"].sudo().set_param("ba_upgrade_sync.api_key", "dummy")
        cursor = self.config.last_cursor
        config_cls = type(self.config)
        with patch.object(config_cls, "_jsonrpc", side_effect=SyncTransientError("down")):
            with self.assertRaises(Exception):
                self.config.action_fetch()
        self.assertEqual(self.config.last_cursor, cursor)

    def test_fetch_stores_new_events_and_moves_cursor(self):
        self.config.write({"source_url": "https://odoo17.invalid", "source_db": "db", "source_login": "sync",
                           "last_cursor": 0})
        self.env["ir.config_parameter"].sudo().set_param("ba_upgrade_sync.api_key", "dummy")
        snap = self.partner_snap(700009, "Fetched Ltd", "fetch@example.com")
        remote = [{"id": 42, "name": str(uuid.uuid4()), "event_type": "partner.upsert", "model": "res.partner",
                   "res_id": 700009, "res_name": "Fetched Ltd", "root_model": "res.partner", "root_id": 700009,
                   "user_login": "admin", "create_date": "2026-09-22 10:00:00",
                   "payload": json.dumps({"record": snap, "extra": {}})}]
        config_cls = type(self.config)
        with patch.object(config_cls, "_remote_execute", side_effect=[remote, []]):
            self.assertEqual(self.config._fetch_events(), 1)
        self.assertEqual(self.config.last_cursor, 42)
        with patch.object(config_cls, "_remote_execute", side_effect=[remote, []]):
            self.assertEqual(self.config._fetch_events(), 0, "same event fetched twice is stored once")

    def test_mvp_flow_customer_to_posted_invoice(self):
        """Customer -> opportunity -> quotation -> sent -> sale order -> invoice -> posted."""
        partner_snap = self.partner_snap(700010, "ABC Ltd", "abc@example.com")
        partner = self.partner_ref(700010, "ABC Ltd", "abc@example.com")
        lead_snap = {"model": "crm.lead", "id": 710010, "name": "ABC opportunity", "type": "opportunity",
                     "create_date": "2026-09-22T09:00:00", "partner_id": partner,
                     "company_id": self.ref(self.company), "expected_revenue": 200.0, "priority": "1"}
        line = self.product_line(810020, qty=2, price=100.0)
        sale = self.sale_snap(800010, partner, [line], opportunity_id={
            "model": "crm.lead", "id": 710010, "name": "ABC opportunity", "create_date": "2026-09-22T09:00:00",
            "keys": {"name": "ABC opportunity"}},
            amount_untaxed=200.0, amount_tax=0.0, amount_total=200.0)
        invoice = {
            "model": "account.move", "id": 820010, "name": "INV/2026/00001", "move_type": "out_invoice",
            "state": "draft", "create_date": "2026-09-22T11:00:00", "partner_id": partner,
            "company_id": self.ref(self.company), "invoice_date": "2026-09-22",
            "sale_order_ids": [{"model": "sale.order", "id": 800010, "name": "S800010",
                                "create_date": "2026-09-21T10:00:00", "keys": {}}],
            "amount_untaxed": 200.0, "amount_tax": 0.0, "amount_total": 200.0,
            "lines": [{"id": 830010, "sequence": 10, "display_type": "product", "name": "Service",
                       "product_id": self.product_ref(), "quantity": 2.0, "price_unit": 100.0,
                       "discount": 0.0, "tax_ids": [],
                       "sale_line_ids": [{"model": "sale.order.line", "id": 810020, "name": "Service",
                                          "create_date": None, "keys": {}}]}],
        }
        root = ("sale.order", 800010)
        events = self.Event
        for event_type, snap, ev_root in [
            ("partner.upsert", partner_snap, None),
            ("lead.upsert", lead_snap, None),
            ("sale.upsert", sale, None),
            ("sale.sent", dict(sale, state="sent"), None),
            ("sale.confirm", dict(sale, state="sale"), None),
            ("invoice.create_from_sale", invoice, root),
            ("invoice.post", dict(invoice, state="posted"), root),
        ]:
            events |= self.make_event(event_type, snap, root=ev_root)[0]
        events.action_process_now()
        for event in events:
            self.assertEqual(event.state, "success", "%s: %s" % (event.event_type, event.error_message))

        order = self.target("sale.order", 800010)
        move = self.target("account.move", 820010)
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.opportunity_id, self.target("crm.lead", 710010))
        self.assertEqual(move.state, "posted")
        self.assertIn(order, move.invoice_line_ids.sale_line_ids.order_id)
        confirm = events.filtered(lambda e: e.event_type == "sale.confirm")
        self.assertIn(confirm.comparison_result, ("match", "mismatch"))
        self.assertTrue(confirm.comparison_html)

    def test_confirm_runs_proquotes_confirmation_activities(self):
        """Custom workflow: proquotes _action_confirm creates activities from
        the active confirmation templates; the replay must trigger it."""
        activity_type = self.env.ref("mail.mail_activity_data_todo")
        self.env["proquotes.confirmation.activity.template"].create({
            "name": "Upgrade sync follow-up", "activity_type_id": activity_type.id,
            "user_id": self.env.user.id, "days_after_confirmation": 1, "order_type": "sale", "active": True,
        })
        partner = self.partner_ref(700011, "Custom Ltd", "custom@example.com")
        self.make_event("partner.upsert", self.partner_snap(700011, "Custom Ltd", "custom@example.com"))[0] \
            .action_process_now()
        event, _r = self.make_event(
            "sale.confirm", self.sale_snap(800011, partner, [self.product_line(810030)], state="sale"))
        event.action_process_now()
        self.assertEqual(event.state, "success", event.error_message)
        order = self.target("sale.order", 800011)
        self.assertIn("Upgrade sync follow-up", order.activity_ids.mapped("summary"))

    def test_comparator_detects_mismatch(self):
        partner = self.partner_ref(700012, "Cmp Ltd", "cmp@example.com")
        self.make_event("partner.upsert", self.partner_snap(700012, "Cmp Ltd", "cmp@example.com"))[0] \
            .action_process_now()
        snap = self.sale_snap(800012, partner, [self.product_line(810040)])
        event, _r = self.make_event("sale.upsert", snap)
        event.action_process_now()
        order = self.target("sale.order", 800012)
        comparator = self.env["upgrade.sync.comparator"]
        payload = event._get_payload()
        payload["record"].update(amount_untaxed=order.amount_untaxed, amount_tax=order.amount_tax,
                                 amount_total=order.amount_total)
        self.assertEqual(comparator._compare(event, payload, order)[0], "match")
        payload["record"]["amount_total"] = order.amount_total + 50
        self.assertEqual(comparator._compare(event, payload, order)[0], "mismatch")
