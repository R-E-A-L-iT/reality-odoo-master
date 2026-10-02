from odoo.tests.common import TransactionCase


class TestLeicaLeadNumber(TransactionCase):

    def test_create_strips_leading_hash(self):
        lead = self.env["crm.lead"].create({
            "name": "Portal lead",
            "leica_lead_number": "#123",
        })
        self.assertEqual(lead.leica_lead_number, "123")

    def test_search_hash_and_digits_for_equal_and_ilike(self):
        lead = self.env["crm.lead"].create({
            "name": "Portal lead",
            "leica_lead_number": "123",
        })
        Lead = self.env["crm.lead"]
        for term in ("#123", "123", " #123 "):
            for operator in ("=", "ilike"):
                found = Lead.search([("leica_lead_number", operator, term)])
                self.assertIn(lead, found)

    def test_write_strips_leading_hash(self):
        lead = self.env["crm.lead"].create({
            "name": "Portal lead",
            "leica_lead_number": "999",
        })
        lead.write({"leica_lead_number": "#123"})
        self.assertEqual(lead.leica_lead_number, "123")

    def test_search_domain_leaves_other_fields_alone(self):
        domain = [
            "|",
            ("name", "ilike", "#123"),
            ("leica_lead_number", "ilike", "#123"),
            ("leica_lead_number", "in", ["#123", "999"]),
        ]
        normalized = self.env["crm.lead"]._normalize_leica_lead_number_domain(domain)
        self.assertEqual(domain[1], ("name", "ilike", "#123"))
        self.assertEqual(domain[2], ("leica_lead_number", "ilike", "#123"))
        self.assertEqual(normalized[1], ("name", "ilike", "#123"))
        self.assertEqual(normalized[2], ("leica_lead_number", "ilike", "123"))
        self.assertEqual(normalized[3], ("leica_lead_number", "in", ["123", "999"]))
