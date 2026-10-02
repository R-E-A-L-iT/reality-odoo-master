# -*- coding: utf-8 -*-
"""Pure tests for portal rental dates. Run without an Odoo database:

    python3 proquotes/tests/test_rental_portal_dates.py
"""

import ast
import importlib.util
import unittest
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_spec = importlib.util.spec_from_file_location(
    "rental_portal_dates", ROOT / "models" / "rental_portal_dates.py"
)
_dates = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_dates)

MESSAGES = _dates.MESSAGES
choose_tz_name = _dates.choose_tz_name
local_midnight_to_utc = _dates.local_midnight_to_utc
paid_rental_days = _dates.paid_rental_days
parse_portal_date = _dates.parse_portal_date
portal_calendar_date = _dates.portal_calendar_date
rental_calendar_days = _dates.rental_calendar_days
rental_dates_editable = _dates.rental_dates_editable
rental_message = _dates.rental_message
sign_block_reason = _dates.sign_block_reason
signature_default_name = _dates.signature_default_name
validate_portal_rental_pair = _dates.validate_portal_rental_pair

class PortalRentalDateTests(unittest.TestCase):
    def test_rejects_missing_malformed_and_impossible_days(self):
        self.assertEqual(validate_portal_rental_pair("", "2026-09-20"), "invalid")
        self.assertEqual(validate_portal_rental_pair("2026-09-17", ""), "invalid")
        self.assertEqual(validate_portal_rental_pair("09/17/2026", "2026-09-20"), "invalid")
        self.assertEqual(validate_portal_rental_pair("2026-02-31", "2026-03-02"), "invalid")
        self.assertIsNone(parse_portal_date("2026-02-31"))

    def test_rejects_start_after_end_and_allows_same_day(self):
        # Typing "20" over "29" passes through 2026-09-02, which is before
        # a start of 2026-09-17. That pair must not be saved.
        self.assertEqual(
            validate_portal_rental_pair("2026-09-17", "2026-09-02"), "order"
        )
        self.assertIsNone(validate_portal_rental_pair("2026-09-17", "2026-09-20"))
        self.assertIsNone(validate_portal_rental_pair("2026-09-17", "2026-09-17"))

    def test_toronto_summer_and_winter_round_trip(self):
        summer = local_midnight_to_utc("2026-09-17", "America/Toronto")
        winter = local_midnight_to_utc("2026-01-17", "America/Toronto")
        self.assertEqual(summer, datetime(2026, 9, 17, 4, 0, 0))
        self.assertEqual(winter, datetime(2026, 1, 17, 5, 0, 0))
        self.assertEqual(portal_calendar_date(summer, "America/Toronto"), "2026-09-17")
        self.assertEqual(portal_calendar_date(winter, "America/Toronto"), "2026-01-17")
        # Pricing uses the UTC calendar date. For Toronto local midnight that
        # date is the day the customer picked.
        self.assertEqual(summer.date().isoformat(), "2026-09-17")
        self.assertEqual(winter.date().isoformat(), "2026-01-17")

    def test_dst_boundary_keeps_the_day_count(self):
        # 2026-03-08 is the DST start. Midnight is still EST; the 9th is EDT.
        start = local_midnight_to_utc("2026-03-07", "America/Toronto")
        end = local_midnight_to_utc("2026-03-10", "America/Toronto")
        self.assertEqual(start, datetime(2026, 3, 7, 5, 0, 0))
        self.assertEqual(end, datetime(2026, 3, 10, 4, 0, 0))
        self.assertEqual(rental_calendar_days(start, end), 3)
        self.assertEqual(portal_calendar_date(start, "America/Toronto"), "2026-03-07")
        self.assertEqual(portal_calendar_date(end, "America/Toronto"), "2026-03-10")

    def test_legacy_midnight_utc_keeps_the_portal_day(self):
        # Existing portal saves: the typed day at 00:00 UTC. Converting to
        # Toronto would show the previous evening. The portal day stays.
        legacy_start = datetime(2026, 9, 17, 0, 0, 0)
        legacy_end = datetime(2026, 9, 20, 0, 0, 0)
        self.assertEqual(portal_calendar_date(legacy_start, "America/Toronto"), "2026-09-17")
        self.assertEqual(portal_calendar_date(legacy_end, "America/Toronto"), "2026-09-20")
        self.assertEqual(rental_calendar_days(legacy_start, legacy_end), 3)

        new_start = local_midnight_to_utc("2026-09-17", "America/Toronto")
        new_end = local_midnight_to_utc("2026-09-20", "America/Toronto")
        self.assertEqual(rental_calendar_days(new_start, new_end), 3)
        self.assertEqual(portal_calendar_date(new_start, "America/Toronto"), "2026-09-17")
        self.assertEqual(portal_calendar_date(new_end, "America/Toronto"), "2026-09-20")

    def test_resaving_legacy_days_does_not_change_the_count(self):
        # Staff moved SO 4070 to 2026-09-18/21 00:00 UTC. Leaving it alone
        # keeps that portal day. Saving those same days stores local midnight
        # and the day count stays 3.
        stored_start = datetime(2026, 9, 18, 0, 0, 0)
        stored_end = datetime(2026, 9, 21, 0, 0, 0)
        shown_start = portal_calendar_date(stored_start, "America/Toronto")
        shown_end = portal_calendar_date(stored_end, "America/Toronto")
        self.assertEqual((shown_start, shown_end), ("2026-09-18", "2026-09-21"))
        rewritten_start = local_midnight_to_utc(shown_start, "America/Toronto")
        rewritten_end = local_midnight_to_utc(shown_end, "America/Toronto")
        self.assertEqual(rental_calendar_days(stored_start, stored_end), 3)
        self.assertEqual(rental_calendar_days(rewritten_start, rewritten_end), 3)
        self.assertNotEqual(rewritten_start, stored_start)

    def test_paid_days_match_the_quote_formula(self):
        self.assertEqual(paid_rental_days(0), 0)
        self.assertEqual(paid_rental_days(1), 1)
        self.assertEqual(paid_rental_days(3), 3)
        self.assertEqual(paid_rental_days(61), 25)

    def test_sign_blocks_only_a_rental_with_a_bad_period(self):
        start = datetime(2026, 9, 17, 4, 0, 0)
        end = datetime(2026, 9, 20, 4, 0, 0)
        self.assertIsNone(sign_block_reason(False, False, False))
        self.assertIsNone(sign_block_reason(True, start, end))
        self.assertIsNone(sign_block_reason(True, start, start))
        self.assertEqual(sign_block_reason(True, False, end), "missing_sign")
        self.assertEqual(sign_block_reason(True, start, False), "missing_sign")
        self.assertEqual(sign_block_reason(True, end, start), "order")

    def test_messages_english_and_french(self):
        self.assertIn("on or before", rental_message("order", "en_CA"))
        self.assertIn("antérieure ou égale", rental_message("order", "fr_CA"))
        self.assertIn("before signing", rental_message("missing_sign", "en_US"))
        self.assertIn("avant de signer", rental_message("missing_sign", "fr_FR"))
        self.assertEqual(rental_message("order", "es_ES"), MESSAGES["order"]["en"])
        self.assertIn("no longer be changed", rental_message("locked", "en_CA"))
        self.assertIn("ne peuvent plus", rental_message("locked", "fr_CA"))

    def test_dates_editable_only_on_unlocked_draft_or_sent(self):
        self.assertTrue(rental_dates_editable("draft", False))
        self.assertTrue(rental_dates_editable("sent", False))
        self.assertFalse(rental_dates_editable("draft", True))
        self.assertFalse(rental_dates_editable("sent", True))
        self.assertFalse(rental_dates_editable("sale", False))
        self.assertFalse(rental_dates_editable("done", False))
        self.assertFalse(rental_dates_editable("cancel", False))
        self.assertFalse(rental_dates_editable(False, False))

    def test_signature_prefill_is_the_customer_for_public_and_portal_users(self):
        customer = "Jane Customer"
        public_user = "Public user for R-E-A-L.iT Solutions"
        portal_user = "Jane Portal"
        # Anonymous visitor: do not prefill the website public user.
        self.assertEqual(signature_default_name(customer, public_user, True), customer)
        # Logged-in portal user: still the order partner, not env.user.
        self.assertEqual(signature_default_name(customer, portal_user, False), customer)
        self.assertNotIn("public user", signature_default_name(customer, public_user, True).lower())
        self.assertEqual(signature_default_name(None, public_user, True), "")

    def test_choose_tz_skips_blanks(self):
        self.assertEqual(
            choose_tz_name(["", "Not/AZone", "America/Toronto"]),
            "America/Toronto",
        )
        self.assertEqual(choose_tz_name([None, ""]), "UTC")

    def test_template_uses_portal_dates_and_the_same_messages(self):
        xml = (ROOT / "views/Quote/quote_preview.xml").read_text(encoding="utf-8")
        ET.fromstring(xml)
        self.assertIn("portal_rental_date(sale_order.rental_start_date)", xml)
        self.assertIn("portal_rental_date(sale_order.rental_return_date)", xml)
        self.assertIn('id="rental-dates-error"', xml)
        self.assertIn("t-att-min=", xml)
        self.assertNotIn(
            "rental_start_date.strftime('%Y-%m-%d')",
            xml,
        )
        for key in ("order", "invalid", "save", "locked"):
            self.assertIn(MESSAGES[key]["en"], xml)
            self.assertIn(MESSAGES[key]["fr"], xml)
        self.assertIn("portal_rental_dates_editable()", xml)
        self.assertIn("t-att-disabled=\"None if rental_dates_editable else 'disabled'\"", xml)
        self.assertIn(
            't-set="default_name" t-value="sale_order.portal_signature_default_name()"',
            xml,
        )
        self.assertNotIn('t-value="env.user.name"', xml)

    def test_controller_validates_before_write_and_sign_before_signature(self):
        rental = (ROOT / "controllers/rental.py").read_text(encoding="utf-8")
        accept = (ROOT / "controllers/controllers.py").read_text(encoding="utf-8")
        update = rental.split("def update_rental_dates", 1)[1].split("def _rental_dates_payload", 1)[0]
        self.assertLess(update.index("portal_rental_dates_editable"), update.index(".write("))
        self.assertLess(update.index("validate_portal_rental_pair"), update.index(".write("))
        self.assertIn('return {"error": rental_message("locked", lang)}', update)
        self.assertIn('return {"error": rental_message(reason, lang)}', update)
        self.assertIn("ValidationError", rental)
        sign = accept.split("def portal_quote_accept", 1)[1]
        self.assertLess(sign.index("portal_rental_sign_error"), sign.index("'signed_by'"))
        model = (ROOT / "models/sale_order.py").read_text(encoding="utf-8")
        self.assertIn("rental_period_coherence", model)
        self.assertIn("rental_start_date <= rental_return_date", model)
        self.assertIn("def portal_signature_default_name", model)
        self.assertIn("self.partner_id.name", model.split("def portal_signature_default_name", 1)[1].split("def portal_rental_sign_error", 1)[0])

    def test_python_modules_parse(self):
        for path in (
            ROOT / "models/rental_portal_dates.py",
            ROOT / "models/sale_order.py",
            ROOT / "controllers/rental.py",
            ROOT / "controllers/controllers.py",
        ):
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


if __name__ == "__main__":
    unittest.main()
