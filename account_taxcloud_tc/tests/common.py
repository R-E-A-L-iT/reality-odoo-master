import os
from unittest import skipIf

from odoo.tests.common import TransactionCase, tagged


@tagged("-standard", "external")
@skipIf(
    not os.getenv("TAXCLOUD_LOGIN_ID" or not os.getenv("TAXCLOUD_API_KEY")),
    "no taxcloud credentials",
)
class TestAccountTaxcloudCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.TAXCLOUD_LOGIN_ID = os.getenv("TAXCLOUD_LOGIN_ID")
        cls.TAXCLOUD_API_KEY = os.getenv("TAXCLOUD_API_KEY")

        # Save Taxcloud credential and sync TICs
        config = cls.env["res.config.settings"].create(
            {
                "taxcloud_api_id": cls.TAXCLOUD_LOGIN_ID,
                "taxcloud_api_key": cls.TAXCLOUD_API_KEY,
            }
        )
        config.sync_taxcloud_category()
        tic_computer = cls.env["product.tic.category"].search([("code", "=", 30100)])
        config.tic_category_id = tic_computer
        config.execute()

        # Some data we'll need
        cls.fiscal_position = cls.env.ref(
            "account_taxcloud_tc.account_fiscal_position_taxcloud_us"
        )
        cls.journal = cls.env["account.journal"].search(
            [
                ("type", "=", "sale"),
                ("company_id", "=", cls.env.ref("base.main_company").id),
            ],
            limit=1,
        )

        # Update address of company
        company = cls.env.user.company_id
        company.write(
            {
                "street": "250 Executive Park Blvd",
                "city": "San Francisco",
                "state_id": cls.env.ref("base.state_us_5").id,
                "country_id": cls.env.ref("base.us").id,
                "zip": "94134",
            }
        )

        # Create partner with correct US address
        cls.partner = cls.env["res.partner"].create(
            {
                "name": "Sale Partner",
                "street": "77 Santa Barbara Rd",
                "city": "Pleasant Hill",
                "state_id": cls.env.ref("base.state_us_5").id,
                "country_id": cls.env.ref("base.us").id,
                "zip": "94523",
            }
        )

        # Create products
        cls.product = cls.env["product.product"].create(
            {
                "name": "Test Product",
                "list_price": 1000.00,
                "standard_price": 200.00,
                "supplier_taxes_id": None,
            }
        )
        cls.product_1 = cls.env["product.product"].create(
            {
                "name": "Test 1 Product",
                "list_price": 100.00,
                "standard_price": 50.00,
                "supplier_taxes_id": None,
            }
        )
        return res
