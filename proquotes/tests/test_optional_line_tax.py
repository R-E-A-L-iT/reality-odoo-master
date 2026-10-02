# -*- coding: utf-8 -*-
from unittest.mock import patch

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
