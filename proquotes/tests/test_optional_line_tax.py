# -*- coding: utf-8 -*-
import json
from unittest.mock import patch

from lxml import etree

from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOptionalLineTax(TransactionCase):
    """Unselected optional lines must not add their tax to stored totals."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'Optional Line Tax Customer',
            'is_company': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Optional Line Tax Product',
            'type': 'service',
            'list_price': 100.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })
        cls.tax = cls.env['account.tax'].create({
            'name': 'Optional line HST 13%',
            'amount_type': 'percent',
            'amount': 13.0,
            'type_tax_use': 'sale',
            'price_include': False,
            'company_id': cls.company.id,
        })
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Optional line tax pricelist',
            'currency_id': cls.company.currency_id.id,
            'company_id': cls.company.id,
        })

    def _create_quote(self):
        """One selected 100.00 line and one unselected optional 50.00 line.

        No quotation template, so rental and renewal template logic does not
        add lines. Canadian tax automation runs from sale.order.create even
        when the caller passes skip_apply_canadian_sales_taxes (that create
        forces the flag back off), so the test tax and prices are pinned
        afterwards.
        """
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
            'company_id': self.company.id,
            'order_line': [
                Command.create({
                    'sequence': 1,
                    'product_id': self.product.id,
                    'name': 'Selected line',
                    'product_uom_qty': 1.0,
                    'price_unit': 100.0,
                    'selected': 'true',
                    'is_selected': True,
                    'optional': 'no',
                    'is_optional': False,
                    'tax_id': [Command.set(self.tax.ids)],
                }),
                Command.create({
                    'sequence': 2,
                    'product_id': self.product.id,
                    'name': 'Unselected optional line',
                    'product_uom_qty': 1.0,
                    'price_unit': 50.0,
                    'selected': 'false',
                    'is_selected': False,
                    'optional': 'yes',
                    'is_optional': True,
                    'tax_id': [Command.set(self.tax.ids)],
                }),
            ],
        })
        self.assertEqual(len(order.order_line), 2)
        for line in order.order_line:
            line.with_context(skip_apply_canadian_sales_taxes=True).write({
                'price_unit': 100.0 if line.sequence == 1 else 50.0,
                'tax_id': [Command.set(self.tax.ids)],
                'selected': 'true' if line.sequence == 1 else 'false',
            })
        return order

    def _assert_amounts(self, order, untaxed, tax, total):
        self.assertAlmostEqual(order.amount_untaxed, untaxed, places=2)
        self.assertAlmostEqual(order.amount_tax, tax, places=2)
        self.assertAlmostEqual(order.amount_total, total, places=2)
        self.assertAlmostEqual(order.tax_totals['amount_total'], total, places=2)

    def test_unselected_optional_line_excludes_tax(self):
        order = self._create_quote()
        selected = order.order_line.filtered(lambda line: line.sequence == 1)
        optional = order.order_line.filtered(lambda line: line.sequence == 2)

        self.assertEqual(optional.selected, 'false')
        self.assertAlmostEqual(optional.price_subtotal, 0.0, places=2)
        self.assertAlmostEqual(optional.price_tax, 0.0, places=2)
        self.assertAlmostEqual(optional.price_total, 0.0, places=2)
        self.assertAlmostEqual(selected.price_subtotal, 100.0, places=2)
        self.assertAlmostEqual(selected.price_tax, 13.0, places=2)
        self.assertAlmostEqual(selected.price_total, 113.0, places=2)
        self._assert_amounts(order, 100.0, 13.0, 113.0)

        optional.write({'selected': 'true'})
        self._assert_amounts(order, 150.0, 19.50, 169.50)
        self.assertAlmostEqual(optional.price_subtotal, 50.0, places=2)
        self.assertAlmostEqual(optional.price_tax, 6.50, places=2)
        self.assertAlmostEqual(optional.price_total, 56.50, places=2)

        optional.write({'selected': 'false'})
        self.assertAlmostEqual(optional.price_subtotal, 0.0, places=2)
        self.assertAlmostEqual(optional.price_tax, 0.0, places=2)
        self.assertAlmostEqual(optional.price_total, 0.0, places=2)
        self._assert_amounts(order, 100.0, 13.0, 113.0)

    def test_reading_tax_totals_does_not_change_write_date(self):
        """Reading the tax widget must not save the order.

        In tests, write_date comes from the transaction's fixed cr.now() and
        write_uid is the same user, so those values stay equal even if the
        order is saved. The real check is that sale.order._write is not
        called for this order.

        Only the widget is invalidated. Invalidating stored amount fields
        makes their recompute look like a change (empty cache) and the
        following flush calls _write even when the numbers are unchanged.
        """
        order = self._create_quote()
        self.env.flush_all()
        write_date = order.write_date
        write_uid = order.write_uid
        order.invalidate_recordset(['tax_totals'])

        order_model = type(order)
        original_write = order_model._write
        written_ids = []

        def _spy_write(self, vals):
            if order in self:
                written_ids.append(order.id)
            return original_write(self, vals)

        with patch.object(order_model, '_write', autospec=True, side_effect=_spy_write):
            self.assertIn('amount_total', order.tax_totals)
            self.env.flush_all()

        self.assertFalse(written_ids)
        self.assertEqual(order.write_date, write_date)
        self.assertEqual(order.write_uid, write_uid)

    def test_toggle_is_selected_updates_amount_total(self):
        """Toggling is_selected still updates the stored order total.

        The backend checkbox onchange copies is_selected onto selected,
        and the portal writes selected. _compute_amounts depends on both
        is_selected and selected, and it is what stores amount_total.
        """
        order = self._create_quote()
        optional = order.order_line.filtered(lambda line: line.sequence == 2)
        self.assertFalse(optional.is_selected)

        optional.write({'is_selected': True, 'selected': 'true'})
        self.assertTrue(optional.is_selected)
        self._assert_amounts(order, 150.0, 19.50, 169.50)

        optional.write({'is_selected': False, 'selected': 'false'})
        self.assertFalse(optional.is_selected)
        self._assert_amounts(order, 100.0, 13.0, 113.0)

    def _form_read_spec(self):
        """Field spec for the combined sale order form, including line fields."""
        arch = etree.fromstring(self.env['sale.order'].get_view(view_type='form')['arch'])
        spec = {}

        def add_field(target, node):
            name = node.get('name')
            if not name or name in target:
                return
            children = {}
            for sub in node.xpath(
                './tree/field[@name]|./list/field[@name]|./form/field[@name]|./kanban/field[@name]'
            ):
                add_field(children, sub)
            target[name] = {'fields': children} if children else {}

        for node in arch.xpath('//field[@name]'):
            if node.xpath('ancestor::field[@name]'):
                continue
            add_field(spec, node)
        spec.setdefault('amount_total', {})
        spec.setdefault('amount_untaxed', {})
        spec.setdefault('amount_tax', {})
        spec.setdefault('tax_totals', {})
        line_fields = spec.setdefault('order_line', {'fields': {}})['fields']
        for fname in (
            'demo_selected', 'is_selected', 'is_optional', 'selected',
            'price_subtotal', 'price_tax', 'price_total', 'price_unit', 'tax_id',
        ):
            line_fields.setdefault(fname, {})
        order_fields = self.env['sale.order']._fields
        for fname in ('is_rental_order', 'rental_status', 'margin', 'margin_percent'):
            if fname in order_fields:
                spec.setdefault(fname, {})
        return spec

    def test_opening_confirmed_order_does_not_write(self):
        """Reading the confirmed form must not save the order or post tracking.

        Confirmed lines can have is_selected out of sync with selected, and a
        stored total that no longer matches the lines. The form used to write
        the booleans while computing demo_selected, which recomputed and
        tracked amount_total.
        """
        order = self._create_quote()
        order.action_confirm()
        self.assertEqual(order.state, 'sale')
        if 'is_rental_order' in order._fields:
            order.with_context(mail_notrack=True, tracking_disable=True).write({
                'is_rental_order': True,
            })
        self.env.flush_all()
        self.env.cr.precommit.run()

        selected = order.order_line.filtered(lambda line: line.sequence == 1)
        self.env.cr.execute(
            "UPDATE sale_order_line SET is_selected = FALSE WHERE id = %s",
            [selected.id],
        )
        self.env.cr.execute(
            "UPDATE sale_order SET amount_total = 0 WHERE id = %s",
            [order.id],
        )
        self.env.invalidate_all()

        order_model = type(order)
        original_write = order_model._write
        original_post = order_model.message_post
        written_ids = []
        posted_ids = []

        def _spy_write(self, vals):
            if order in self:
                written_ids.append(order.id)
            return original_write(self, vals)

        def _spy_post(self, **kwargs):
            if order in self:
                posted_ids.append(order.id)
            return original_post(self, **kwargs)

        with patch.object(order_model, '_write', autospec=True, side_effect=_spy_write), \
             patch.object(order_model, 'message_post', autospec=True, side_effect=_spy_post):
            order.web_read(self._form_read_spec())
            self.env.cr.flush()

        self.assertFalse(written_ids)
        self.assertFalse(posted_ids)
        self.assertFalse(selected.is_selected)

    def test_approve_items_json_uses_selected_string(self):
        """Approve JSON follows selected, even when is_selected is stale.

        Existing rows can have selected='true' with is_selected false, and
        the reverse. The checkbox boolean is not the filter.
        """
        order = self._create_quote()
        selected = order.order_line.filtered(lambda line: line.sequence == 1)
        unselected = order.order_line.filtered(lambda line: line.sequence == 2)
        self.env.cr.execute(
            "UPDATE sale_order_line SET is_selected = FALSE WHERE id = %s",
            [selected.id],
        )
        self.env.cr.execute(
            "UPDATE sale_order_line SET is_selected = TRUE WHERE id = %s",
            [unselected.id],
        )
        self.env.invalidate_all()

        items = json.loads(order.get_approve_items_json())
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]['model'], selected.product_id.name)
        self.assertEqual(items[0]['quantity'], selected.product_uom_qty)
        self.assertEqual(items[0]['price'], selected.price_unit)
        self.assertEqual(items[0]['type'], 'new_product')

    def test_rental_schedule_uses_selected_string(self):
        """The rental schedule view includes a line by selected, not is_selected.

        selected defaults to 'true' and is required, so a line created the
        way core does (no selected key) is included. NULL, when the column
        allows it, is treated as that default. Explicit 'false' is left out
        even if the checkbox boolean is true.
        """
        if 'sale.rental.schedule' not in self.env:
            self.skipTest('sale_renting is not installed')
        schedule = self.env['sale.rental.schedule']
        query = schedule._query()
        self.assertNotIn('is_selected', query)
        self.assertIn('sol.product_id IS NOT NULL', query)
        self.assertIn('sol.is_rental', query)
        self.assertIn("COALESCE(NULLIF(sol.selected, ''), 'true') = 'true'", query)

        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
            'company_id': self.company.id,
            'order_line': [
                Command.create({
                    'product_id': self.product.id,
                    'name': 'Selected rental line',
                    'product_uom_qty': 1.0,
                    'price_unit': 100.0,
                    'selected': 'true',
                    'is_selected': True,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'name': 'Unselected rental line',
                    'product_uom_qty': 1.0,
                    'price_unit': 50.0,
                    'selected': 'false',
                    'is_selected': False,
                }),
                Command.create({
                    'product_id': self.product.id,
                    'name': 'Default rental line',
                    'product_uom_qty': 1.0,
                    'price_unit': 100.0,
                }),
            ],
        })
        selected = order.order_line.filtered(lambda line: line.name == 'Selected rental line')
        unselected = order.order_line.filtered(lambda line: line.name == 'Unselected rental line')
        default_line = order.order_line.filtered(lambda line: line.name == 'Default rental line')
        self.assertEqual(default_line.selected, 'true')

        self.env.cr.execute(
            """
            UPDATE sale_order_line
               SET is_rental = TRUE,
                   is_selected = CASE WHEN id = %s THEN TRUE ELSE FALSE END
             WHERE id IN %s
            """,
            [unselected.id, tuple(order.order_line.ids)],
        )
        self.env.cr.execute(
            """
            SELECT is_nullable
              FROM information_schema.columns
             WHERE table_name = 'sale_order_line'
               AND column_name = 'selected'
            """
        )
        selected_nullable = self.env.cr.fetchone()[0] == 'YES'
        if selected_nullable:
            self.env.cr.execute(
                "UPDATE sale_order_line SET selected = NULL WHERE id = %s",
                [default_line.id],
            )
        self.env.invalidate_all()
        self.assertFalse(selected.is_selected)
        self.assertTrue(unselected.is_selected)
        self.assertEqual(selected.selected, 'true')
        self.assertEqual(unselected.selected, 'false')

        schedule.init()
        if 'order_line_id' in schedule._fields:
            rows = schedule.search([('order_line_id', 'in', order.order_line.ids)])
            found = set(rows.mapped('order_line_id').ids)
        else:
            rows = schedule.search([('id', 'in', order.order_line.ids)])
            found = set(rows.ids)

        self.assertIn(selected.id, found)
        self.assertIn(default_line.id, found)
        self.assertNotIn(unselected.id, found)
