from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

from odoo.tests.common import TransactionCase


class TestAccountTaxcloudCommon(TransactionCase):
    @contextmanager
    def mock_taxcloud(self):
        return_get_all_taxes_values = {
            "response": {
                "ResponseType": "OK",
                "Messages": None,
                "CartID": "443",
                "CartItemsResponse": {
                    "CartItemResponse": [
                        {"CartItemIndex": 0, "TaxAmount": 6.41},
                        {"CartItemIndex": 1, "TaxAmount": 0.641},
                    ]
                },
            },
            "values": {0: 6.41, 1: 0.641},
        }
        return_get_tic_category_value = {
            "data": [
                {"Description": "Mock TIC Code 1", "TICID": "0001"},
                {"Description": "Mock TIC Code 2", "TICID": "0002"},
            ]
        }
        return_verify_address_value = {
            "Address1": "250 Executive Park Blvd",
            "Address2": "",
            "City": "San Francisco",
            "State": self.env.ref("base.state_us_5").id,
            "Zip4": "94134",
            "Zip5": "",
        }

        authorize_with_capture_mock_response = MagicMock()
        authorize_with_capture_mock_response.ResponseType = "Success"
        authorize_with_capture_mock_response.Messages = [
            "Authorize and Captured in Taxcloud"
        ]

        returned_mock_response = MagicMock()
        returned_mock_response.ResponseType = "Success"
        returned_mock_response.Messages = ["Returned from Taxcloud"]

        captured_mock_response = MagicMock()
        captured_mock_response.ResponseType = "Success"
        captured_mock_response.Messages = ["Returned from Taxcloud"]

        try:
            base = "odoo.addons.account_taxcloud_tc.models.taxcloud_request.TaxCloudRequest"

            with patch(
                f"{base}.verify_address",
                new=Mock(return_value=return_verify_address_value),
            ), patch(
                f"{base}.get_tic_category",
                new=Mock(return_value=return_get_tic_category_value),
            ), patch(
                f"{base}.get_all_taxes_values",
                new=Mock(return_value=return_get_all_taxes_values),
            ), patch(
                f"{base}.get_taxcloud_authorize_with_capture",
                new=Mock(return_value=authorize_with_capture_mock_response),
            ), patch(
                f"{base}.get_taxcloud_returned",
                new=Mock(return_value=returned_mock_response),
            ), patch(
                f"{base}.get_taxcloud_captured",
                new=Mock(return_value=captured_mock_response),
            ):
                yield
        finally:
            pass

    @classmethod
    def setUpClass(cls):
        res = super().setUpClass()
        cls.TAXCLOUD_LOGIN_ID = "TAXCLOUD_LOGIN_ID"
        cls.TAXCLOUD_API_KEY = "TAXCLOUD_API_KEY"

        # Save Taxcloud credential and sync TICs
        config = cls.env["res.config.settings"].create(
            {
                "taxcloud_api_id": cls.TAXCLOUD_LOGIN_ID,
                "taxcloud_api_key": cls.TAXCLOUD_API_KEY,
            }
        )
        with cls.mock_taxcloud(cls):
            config.sync_taxcloud_category()
            tic_computer = cls.env["product.tic.category"].search(
                [("code", "=", "0001")]
            )
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

        # Set invoice policies to ordered, so the products
        # can be invoiced without having to deal with the delivery
        # cls.product.product_tmpl_id.invoice_policy = "order"
        # cls.product_1.product_tmpl_id.invoice_policy = "order"

        return res
