# -*- coding: utf-8 -*-
"""
ProSync test suite.

Each test builds a small in-memory "sheet" (a list of lists, exactly the shape
gspread's `worksheet.get_all_values()` returns: row 0 is the header row, every
other row is data) and feeds it straight into the relevant syncer class,
bypassing Google entirely (no gspread/oauth2client/network dependency, no
Google credentials required). This mirrors exactly what
`prosync.sync.start_sync_process` does after it fetches a tab from Google —
the syncers themselves never talk to Google directly.

Run with:
    ./odoo-bin -c <conf> -d <test_db> -i prosync \
        --test-enable --test-tags prosync --stop-after-init
"""
import json
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tests import tagged

from ..models.sync.product_template import product_template_sync
from ..models.sync.stock_lot import stock_lot_sync
from ..models.sync.res_partner import res_partner_sync
from ..models.sync.mrp_bom import mrp_bom_sync
from ..models.sync.mrp_bom_line import mrp_bom_line_sync
from ..models.start_sync import ProsyncSync


def sheet(header, *rows):
    """Build a gspread-shaped sheet: [header, row1, row2, ...]."""
    return [header] + [list(row) for row in rows]


@tagged('post_install', '-at_install', 'prosync')
class ProSyncTestCase(TransactionCase):
    """Shared fixtures for every syncer: currencies, companies, pricelists
    and vendor partners that utilities.py hardcodes by name (price/rental
    price/vendor special-column handling all look these up by exact name).
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Report = cls.env['prosync.report']

        cls.usd = cls.env.ref('base.USD')
        cls.cad = cls.env.ref('base.CAD')
        (cls.usd + cls.cad).sudo().write({'active': True})

        cls.company_us = cls.env['res.company'].create({
            'name': 'R-E-A-L.iT U.S. Inc.', 'currency_id': cls.usd.id,
        })
        cls.company_ca = cls.env['res.company'].create({
            'name': 'R-E-A-L.iT Solutions', 'currency_id': cls.cad.id,
        })
        cls.company_main = cls.env['res.company'].create({
            'name': 'R-E-A-L.iT', 'currency_id': cls.cad.id,
        })

        cls.pricelist_usd = cls.env['product.pricelist'].create({
            'name': '\U0001F1FA\U0001F1F8', 'currency_id': cls.usd.id,
        })
        cls.pricelist_cad = cls.env['product.pricelist'].create({
            'name': '\U0001F1E8\U0001F1E6', 'currency_id': cls.cad.id,
        })
        cls.pricelist_usd_rental = cls.env['product.pricelist'].create({
            'name': 'USD RENTAL', 'currency_id': cls.usd.id,
        })
        cls.pricelist_cad_rental = cls.env['product.pricelist'].create({
            'name': 'CAD RENTAL', 'currency_id': cls.cad.id,
        })

        cls.vendor_cad = cls.env['res.partner'].create({
            'name': 'Leica Geosystems Ltd.', 'is_company': True,
        })
        cls.vendor_usd = cls.env['res.partner'].create({
            'name': 'Leica Geosystems Inc', 'is_company': True,
        })

    def _reports(self, sync_type):
        return self.Report.search([('sync_type', '=', sync_type)])


# ---------------------------------------------------------------------------
# product_template_sync
# ---------------------------------------------------------------------------
@tagged('post_install', '-at_install', 'prosync')
class TestProductTemplateSync(ProSyncTestCase):

    def _run(self, name, *rows, header=None):
        header = header or ["sku", "name", "valid", "continue"]
        syncer = product_template_sync(
            name=name, sheet=sheet(header, *rows), database=self.env)
        syncer.sync_product_template()
        return syncer

    def test_create_minimal_product(self):
        """A brand-new SKU is created; a bare create with no field diffs
        leaves no report behind (report_id.unlink() when nothing changed)."""
        self._run("Products", ["SKU-100", "Widget", "TRUE", "TRUE"])
        product = self.env['product.template'].search([('sku', '=', 'SKU-100')])
        self.assertTrue(product, "product.template should have been created")
        self.assertEqual(product.name, "Widget")
        self.assertFalse(
            self.Report.search([('name', '=', 'Product Template Sync: Products')]),
            "no-op sync should not leave a report behind",
        )

    def test_update_existing_product_writes_report(self):
        self.env['product.template'].create({'sku': 'SKU-200', 'name': 'Old Name'})
        self._run("Products", ["SKU-200", "New Name", "TRUE", "TRUE"])
        product = self.env['product.template'].search([('sku', '=', 'SKU-200')])
        self.assertEqual(product.name, "New Name")
        report = self.Report.search([('name', '=', 'Product Template Sync: Products')])
        self.assertTrue(report, "a field change should leave a report")
        self.assertEqual(report.status, 'success')
        self.assertIn('New Name', report.report_text)

    def test_missing_sku_produces_warning_not_crash(self):
        self._run("Products", ["", "No SKU Product", "TRUE", "TRUE"])
        report = self.Report.search([('name', '=', 'Product Template Sync: Products')])
        self.assertEqual(report.status, 'warning')
        self.assertIn('missing a valid SKU', report.warning_text)

    def test_valid_false_continue_true_skips_row(self):
        self._run(
            "Products",
            ["SKU-301", "Skip Me", "FALSE", "TRUE"],
            ["SKU-302", "Process Me", "TRUE", "TRUE"],
        )
        self.assertFalse(self.env['product.template'].search([('sku', '=', 'SKU-301')]))
        self.assertTrue(self.env['product.template'].search([('sku', '=', 'SKU-302')]))

    def test_valid_false_continue_false_stops_sync(self):
        self._run(
            "Products",
            ["SKU-401", "Stop Here", "FALSE", "FALSE"],
            ["SKU-402", "Never Reached", "TRUE", "TRUE"],
        )
        self.assertFalse(self.env['product.template'].search([('sku', '=', 'SKU-401')]))
        self.assertFalse(self.env['product.template'].search([('sku', '=', 'SKU-402')]))

    def test_related_field_resolves_many2one(self):
        category = self.env['product.category'].create({'name': 'ProSync Test Category'})
        header = ["sku", "name", "categ_id[related=name]", "valid", "continue"]
        self._run("Products", ["SKU-500", "Categorized", "ProSync Test Category", "TRUE", "TRUE"], header=header)
        product = self.env['product.template'].search([('sku', '=', 'SKU-500')])
        self.assertEqual(product.categ_id, category)

    def test_price_pricelist_creates_and_updates(self):
        header = ["sku", "name", "price[pricelist=CAD]", "valid", "continue"]
        self._run("Products", ["SKU-600", "Priced Item", "199.99", "TRUE", "TRUE"], header=header)
        product = self.env['product.template'].search([('sku', '=', 'SKU-600')])
        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', self.pricelist_cad.id),
            ('product_tmpl_id', '=', product.id),
            ('applied_on', '=', '1_product'),
        ])
        self.assertEqual(len(item), 1)
        self.assertEqual(item.fixed_price, 199.99)

        self._run("Products", ["SKU-600", "Priced Item", "249.99", "TRUE", "TRUE"], header=header)
        item = self.env['product.pricelist.item'].search([
            ('pricelist_id', '=', self.pricelist_cad.id),
            ('product_tmpl_id', '=', product.id),
            ('applied_on', '=', '1_product'),
        ])
        self.assertEqual(item.fixed_price, 249.99)

    def test_rental_price_currency_shorthand_creates_pricing(self):
        header = ["sku", "name", "rental_price[usd]", "valid", "continue"]
        self._run("Products", ["SKU-700", "Rental Item", "25.50", "TRUE", "TRUE"], header=header)
        product = self.env['product.template'].search([('sku', '=', 'SKU-700')])
        pricing = self.env['product.pricing'].search([
            ('product_template_id', '=', product.id),
            ('pricelist_id', '=', self.pricelist_usd_rental.id),
        ])
        self.assertEqual(len(pricing), 1)
        self.assertEqual(pricing.price, 25.50)

        self._run("Products", ["SKU-700", "Rental Item", "30.00", "TRUE", "TRUE"], header=header)
        pricing = self.env['product.pricing'].search([
            ('product_template_id', '=', product.id),
            ('pricelist_id', '=', self.pricelist_usd_rental.id),
        ])
        self.assertEqual(len(pricing), 1, "existing pricing row should be updated, not duplicated")
        self.assertEqual(pricing.price, 30.00)

    def test_special_purchase_price_creates_supplierinfo(self):
        header = ["sku", "name", "[special=purchase_cad]", "valid", "continue"]
        self._run("Products", ["SKU-800", "Vendor Priced", "450.00", "TRUE", "TRUE"], header=header)
        product = self.env['product.template'].search([('sku', '=', 'SKU-800')])
        info = self.env['product.supplierinfo'].sudo().search([
            ('product_tmpl_id', '=', product.id),
            ('partner_id', '=', self.vendor_cad.id),
            ('currency_id', '=', self.cad.id),
        ])
        self.assertEqual(len(info), 1)
        self.assertEqual(info.price, 450.00)


# ---------------------------------------------------------------------------
# stock_lot_sync
# ---------------------------------------------------------------------------
@tagged('post_install', '-at_install', 'prosync')
class TestStockLotSync(ProSyncTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.template'].create({
            'sku': 'SKU-LOT-1', 'name': 'Lot Tracked Item',
            'is_storable': True, 'tracking': 'serial',
        })

    def _run(self, name, *rows, header=None):
        header = header or ["name", "product_id", "valid", "continue"]
        syncer = stock_lot_sync(name=name, sheet=sheet(header, *rows), database=self.env)
        syncer.sync_stock_lot()
        return syncer

    def test_create_lot(self):
        self._run("Lots", ["SN-0001", "SKU-LOT-1", "TRUE", "TRUE"])
        lot = self.env['stock.lot'].search([('name', '=', 'SN-0001')])
        self.assertTrue(lot)
        self.assertEqual(lot.product_id.sku, 'SKU-LOT-1')

    def test_missing_product_sku_warns(self):
        self._run("Lots", ["SN-0002", "NO-SUCH-SKU", "TRUE", "TRUE"])
        self.assertFalse(self.env['stock.lot'].search([('name', '=', 'SN-0002')]))
        report = self.Report.search([('name', '=', 'Lot/Serial Number Sync: Lots')])
        self.assertEqual(report.status, 'warning')


# ---------------------------------------------------------------------------
# res_partner_sync
# ---------------------------------------------------------------------------
@tagged('post_install', '-at_install', 'prosync')
class TestResPartnerSync(ProSyncTestCase):

    def _run(self, name, *rows, header=None):
        header = header or ["name", "valid", "continue"]
        syncer = res_partner_sync(name=name, sheet=sheet(header, *rows), database=self.env)
        syncer.sync_res_partner()
        return syncer

    def test_create_partner_by_name(self):
        self._run("Contacts", ["Acme Corp", "TRUE", "TRUE"])
        self.assertTrue(self.env['res.partner'].search([('name', '=', 'Acme Corp')]))

    def test_lookup_by_email_when_present(self):
        partner = self.env['res.partner'].create({'name': 'Original Name', 'email': 'dup@example.com'})
        header = ["name", "email", "valid", "continue"]
        self._run("Contacts", ["Renamed Via Email Match", "dup@example.com", "TRUE", "TRUE"], header=header)
        self.assertEqual(partner.name, "Renamed Via Email Match")
        self.assertEqual(
            self.env['res.partner'].search_count([('email', '=', 'dup@example.com')]), 1,
            "should update the existing partner, not create a duplicate",
        )

    def test_related_field_resolves_country(self):
        header = ["name", "country_id[related=code]", "valid", "continue"]
        self._run("Contacts", ["Canadian Co", "CA", "TRUE", "TRUE"], header=header)
        partner = self.env['res.partner'].search([('name', '=', 'Canadian Co')])
        self.assertEqual(partner.country_id.code, "CA")


# ---------------------------------------------------------------------------
# mrp_bom_sync (post-fix: create_mrp_bom no longer NameErrors and now keys
# the parent product by SKU instead of a nonexistent `code` field)
# ---------------------------------------------------------------------------
@tagged('post_install', '-at_install', 'prosync')
class TestMrpBomSync(ProSyncTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent = cls.env['product.template'].create({'sku': 'SKU-KIT-1', 'name': 'Kit Product'})
        cls.component = cls.env['product.template'].create({'sku': 'SKU-COMP-1', 'name': 'Component'})

    def _run(self, name, *rows, header=None):
        header = header or ["product_tmpl_id[related=sku]", "code", "valid", "continue"]
        syncer = mrp_bom_sync(name=name, sheet=sheet(header, *rows), database=self.env)
        syncer.sync_mrp_bom()
        return syncer

    def test_create_bom_header_by_sku(self):
        self._run("BOMs", ["SKU-KIT-1", "BOM-001", "TRUE", "TRUE"])
        bom = self.env['mrp.bom'].search([('code', '=', 'BOM-001')])
        self.assertTrue(bom, "create_mrp_bom should no longer NameError / mis-key by 'code'")
        self.assertEqual(bom.product_tmpl_id, self.parent)

    def test_special_products_column_creates_bom_lines(self):
        header = ["product_tmpl_id[related=sku]", "code", "[special=products]", "valid", "continue"]
        payload = json.dumps([{
            "product_id": "SKU-COMP-1", "product_qty": "2", "product_uom_id": "Units",
        }])
        self._run("BOMs", ["SKU-KIT-1", "BOM-002", payload, "TRUE", "TRUE"], header=header)
        bom = self.env['mrp.bom'].search([('code', '=', 'BOM-002')])
        self.assertTrue(bom)
        self.assertEqual(len(bom.bom_line_ids), 1)
        self.assertEqual(bom.bom_line_ids.product_qty, 2.0)


# ---------------------------------------------------------------------------
# mrp_bom_line_sync — including the stale-line cleanup called out in the docs
# ---------------------------------------------------------------------------
@tagged('post_install', '-at_install', 'prosync')
class TestMrpBomLineSync(ProSyncTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parent = cls.env['product.template'].create({'sku': 'SKU-KIT-2', 'name': 'Kit Product 2'})
        cls.comp_a = cls.env['product.template'].create({'sku': 'SKU-COMP-A', 'name': 'Component A'})
        cls.comp_b = cls.env['product.template'].create({'sku': 'SKU-COMP-B', 'name': 'Component B'})
        cls.bom = cls.env['mrp.bom'].create({'product_tmpl_id': cls.parent.id, 'type': 'phantom'})

    def _run(self, name, *rows, header=None):
        header = header or ["bom_id", "product_id", "product_qty", "valid", "continue"]
        syncer = mrp_bom_line_sync(name=name, sheet=sheet(header, *rows), database=self.env)
        syncer.sync_mrp_bom_line()
        return syncer

    def test_create_and_update_line_quantity(self):
        self._run("BOM Lines", ["SKU-KIT-2", "SKU-COMP-A", "3", "TRUE", "TRUE"])
        line = self.env['mrp.bom.line'].search([
            ('bom_id', '=', self.bom.id), ('product_id.sku', '=', 'SKU-COMP-A'),
        ])
        self.assertEqual(line.product_qty, 3.0)

        self._run("BOM Lines", ["SKU-KIT-2", "SKU-COMP-A", "5", "TRUE", "TRUE"])
        line = self.env['mrp.bom.line'].search([
            ('bom_id', '=', self.bom.id), ('product_id.sku', '=', 'SKU-COMP-A'),
        ])
        self.assertEqual(len(line), 1)
        self.assertEqual(line.product_qty, 5.0)

    def test_stale_line_removed_when_absent_from_sheet(self):
        # Two lines exist in Odoo; the sheet for this BOM only lists one of them.
        self.env['mrp.bom.line'].create({
            'bom_id': self.bom.id, 'product_id': self.comp_a.product_variant_id.id, 'product_qty': 1,
        })
        self.env['mrp.bom.line'].create({
            'bom_id': self.bom.id, 'product_id': self.comp_b.product_variant_id.id, 'product_qty': 1,
        })
        self._run("BOM Lines", ["SKU-KIT-2", "SKU-COMP-A", "1", "TRUE", "TRUE"])

        remaining = self.env['mrp.bom.line'].search([('bom_id', '=', self.bom.id)])
        self.assertEqual(remaining.product_id.mapped('sku'), ['SKU-COMP-A'])


# ---------------------------------------------------------------------------
# prosync.sync orchestration — verifies the ODOO_CONFIGURATION tab dispatch,
# including the previously-missing mrp_bom branch.
# ---------------------------------------------------------------------------
@tagged('post_install', '-at_install', 'prosync')
class TestProsyncOrchestration(ProSyncTestCase):

    def test_dispatches_product_template_sheet_type(self):
        product_row = ["SKU-ORCH-1", "Orchestrated Product", "TRUE", "TRUE"]

        from datetime import date
        today_str = date.today().strftime("%d/%m/%Y")

        configuration_tab = sheet(
            ["NAME", "INDEX", "TYPE", "DATE", "VALID", "CONTINUE"],
            ["Products", "1", "product_template", today_str, "TRUE", "TRUE"],
        )
        products_tab = sheet(["sku", "name", "valid", "continue"], product_row)

        def fake_get_worksheet_by_name(self, pw, sheet_id, sheet_name, expected_index=None):
            return {"Products": products_tab}.get(sheet_name)

        with patch.object(ProsyncSync, 'establish_sheets_connection', lambda self, pw, sheet_id, sheet_num: configuration_tab), \
             patch.object(ProsyncSync, 'get_worksheet_by_name', fake_get_worksheet_by_name), \
             patch.object(ProsyncSync, 'get_master_database_template_id', lambda self, db_name: 'fake-sheet-id'):
            self.env['prosync.sync'].start_sync_process(pw={'fake': 'credentials'})

        self.assertTrue(self.env['product.template'].search([('sku', '=', 'SKU-ORCH-1')]))

    def test_mrp_bom_sheet_type_now_dispatches(self):
        """Regression test for the fixed bug: sheet_type == 'mrp_bom' used to
        fall through to the unsupported-type branch and silently do nothing."""
        parent = self.env['product.template'].create({'sku': 'SKU-ORCH-BOM', 'name': 'Orch Kit'})

        from datetime import date
        today_str = date.today().strftime("%d/%m/%Y")

        configuration_tab = sheet(
            ["NAME", "INDEX", "TYPE", "DATE", "VALID", "CONTINUE"],
            ["BOMs", "1", "mrp_bom", today_str, "TRUE", "TRUE"],
        )
        boms_tab = sheet(
            ["product_tmpl_id[related=sku]", "code", "valid", "continue"],
            ["SKU-ORCH-BOM", "BOM-ORCH-1", "TRUE", "TRUE"],
        )

        def fake_get_worksheet_by_name(self, pw, sheet_id, sheet_name, expected_index=None):
            return {"BOMs": boms_tab}.get(sheet_name)

        with patch.object(ProsyncSync, 'establish_sheets_connection', lambda self, pw, sheet_id, sheet_num: configuration_tab), \
             patch.object(ProsyncSync, 'get_worksheet_by_name', fake_get_worksheet_by_name), \
             patch.object(ProsyncSync, 'get_master_database_template_id', lambda self, db_name: 'fake-sheet-id'):
            self.env['prosync.sync'].start_sync_process(pw={'fake': 'credentials'})

        bom = self.env['mrp.bom'].search([('code', '=', 'BOM-ORCH-1')])
        self.assertTrue(bom)
        self.assertEqual(bom.product_tmpl_id, parent)

    def test_falls_back_to_config_parameter_credentials(self):
        """When called without `pw` (as the cron and the "Run ProSync now"
        button do), start_sync_process should read the service-account key
        from ir.config_parameter instead of crashing on `pw=None`."""
        self.env['ir.config_parameter'].sudo().set_param(
            'prosync.google_service_account_key', json.dumps({'fake': 'credentials'}))

        received = {}

        def fake_establish(self, pw, sheet_id, sheet_num):
            received['pw'] = pw
            return sheet(["NAME", "INDEX", "TYPE", "DATE", "VALID", "CONTINUE"])

        with patch.object(ProsyncSync, 'establish_sheets_connection', fake_establish), \
             patch.object(ProsyncSync, 'get_master_database_template_id', lambda self, db_name: 'fake-sheet-id'):
            self.env['prosync.sync'].start_sync_process()

        self.assertEqual(received.get('pw'), {'fake': 'credentials'})

    def test_no_credentials_available_aborts_without_crash(self):
        self.env['ir.config_parameter'].sudo().set_param('prosync.google_service_account_key', '')
        # Should log an error and return, not raise.
        self.env['prosync.sync'].start_sync_process()
