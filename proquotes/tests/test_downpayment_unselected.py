# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestDownPaymentUnselectedOptional(TransactionCase):
    """Down payments follow the selected lines, not every product line.

    The order total excludes an unselected optional line. The down payment
    share has to use that same base, including the tax split.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'Down Payment Unselected Customer',
            'is_company': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Down Payment Unselected Product',
            'type': 'service',
            'invoice_policy': 'order',
            'list_price': 100.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })
        cls.deposit = cls.env['product.product'].create({
            'name': 'Down Payment Unselected Deposit',
            'type': 'service',
            'invoice_policy': 'order',
            'list_price': 0.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
            'company_id': cls.company.id,
        })
        cls.company.sale_down_payment_product_id = cls.deposit
        cls.selected_tax = cls.env['account.tax'].create({
            'name': 'Down payment unselected HST 13%',
            'amount_type': 'percent',
            'amount': 13.0,
            'type_tax_use': 'sale',
            'price_include': False,
            'company_id': cls.company.id,
        })
        cls.unselected_tax = cls.env['account.tax'].create({
            'name': 'Down payment unselected GST 5%',
            'amount_type': 'percent',
            'amount': 5.0,
            'type_tax_use': 'sale',
            'price_include': False,
            'company_id': cls.company.id,
        })
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Down payment unselected pricelist',
            'currency_id': cls.company.currency_id.id,
            'company_id': cls.company.id,
        })
        cls.header = cls.env['header.footer'].create({
            'name': 'Down payment unselected header',
            'record_type': 'Header',
            'url': 'https://example.com/down-payment-unselected-header.png',
        })
        cls.footer = cls.env['header.footer'].create({
            'name': 'Down payment unselected footer',
            'record_type': 'Footer',
            'url': 'https://example.com/down-payment-unselected-footer.png',
        })

    def _product_vals(self, sequence, name, price, selected, tax):
        return Command.create({
            'sequence': sequence,
            'product_id': self.product.id,
            'name': name,
            'product_uom_qty': 1.0,
            'price_unit': price,
            'selected': 'true' if selected else 'false',
            'is_selected': selected,
            'optional': 'no' if selected else 'yes',
            'is_optional': not selected,
            'is_quantityLocked': True,
            'tax_id': [Command.set(tax.ids)],
        })

    def _confirmed_order(self):
        """One selected line at 100 + 13%, one unselected line at 50 + 5%.

        The selected total is 113. The unselected line keeps its unit price
        and its own tax, and stays out of the order total.
        """
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
            'company_id': self.company.id,
            'header_id': self.header.id,
            'footer_id': self.footer.id,
            'order_line': [
                self._product_vals(1, 'Selected line', 100.0, True, self.selected_tax),
                self._product_vals(2, 'Unselected optional line', 50.0, False, self.unselected_tax),
            ],
        })
        plan = {
            1: ('Selected line', 'true', 100.0, self.selected_tax),
            2: ('Unselected optional line', 'false', 50.0, self.unselected_tax),
        }
        for line in order.order_line:
            name, selected, price, tax = plan[line.sequence]
            line.with_context(skip_apply_canadian_sales_taxes=True).write({
                'name': name,
                'selected': selected,
                'price_unit': price,
                'tax_id': [Command.set(tax.ids)],
            })
        order.action_confirm()
        selected = order.order_line.filtered(lambda line: line.name == 'Selected line')
        unselected = order.order_line.filtered(lambda line: line.name == 'Unselected optional line')
        self.assertEqual(selected.tax_id, self.selected_tax)
        self.assertEqual(unselected.tax_id, self.unselected_tax)
        self.assertAlmostEqual(selected.price_subtotal, 100.0, places=2)
        self.assertAlmostEqual(unselected.price_unit, 50.0, places=2)
        self.assertAlmostEqual(unselected.price_subtotal, 0.0, places=2)
        self.assertAlmostEqual(order.amount_untaxed, 100.0, places=2)
        self.assertAlmostEqual(order.amount_tax, 13.0, places=2)
        self.assertAlmostEqual(order.amount_total, 113.0, places=2)
        return order, selected, unselected

    def _invoice_down_payment(self, order, method, **amounts):
        wizard = self.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order',
            active_ids=order.ids,
            active_id=order.id,
        ).create({
            'advance_payment_method': method,
            'sale_order_ids': [Command.set(order.ids)],
            **amounts,
        })
        wizard.create_invoices()
        invoice = order.invoice_ids
        self.assertEqual(len(invoice), 1)
        return invoice

    def _assert_selected_lines_only(self, order, unselected, untaxed, tax, total):
        payment_lines = order.order_line.filtered(
            lambda line: line.is_downpayment and not line.display_type
        )
        self.assertEqual(len(payment_lines), 1)
        self.assertEqual(payment_lines.tax_id, self.selected_tax)
        self.assertAlmostEqual(payment_lines.price_unit, untaxed, places=2)

        invoice = order.invoice_ids
        self.assertAlmostEqual(invoice.amount_untaxed, untaxed, places=2)
        self.assertAlmostEqual(invoice.amount_tax, tax, places=2)
        self.assertAlmostEqual(invoice.amount_total, total, places=2)
        product_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type not in ('line_section', 'line_note')
        )
        self.assertEqual(len(product_lines), 1)
        self.assertEqual(product_lines.tax_ids, self.selected_tax)
        self.assertAlmostEqual(product_lines.quantity, 1.0, places=2)
        self.assertAlmostEqual(product_lines.price_unit, untaxed, places=2)
        tax_lines = invoice.line_ids.filtered('tax_line_id')
        self.assertEqual(tax_lines.tax_line_id, self.selected_tax)

        self.assertEqual(unselected.qty_to_invoice, 0.0)
        self.assertAlmostEqual(unselected.price_unit, 50.0, places=2)

    def test_percentage_down_payment_uses_selected_lines_only(self):
        order, _selected, unselected = self._confirmed_order()
        self._invoice_down_payment(order, 'percentage', amount=50.0)
        # 50% of the selected 100 untaxed, plus 13% tax. The unselected
        # 50 at 5% is not part of the base.
        self._assert_selected_lines_only(order, unselected, 50.0, 6.50, 56.50)

    def test_fixed_down_payment_uses_selected_lines_only(self):
        order, _selected, unselected = self._confirmed_order()
        self._invoice_down_payment(order, 'fixed', fixed_amount=50.0)
        # 50 / 113 of the selected 100 untaxed is 44.25, tax 5.75.
        # The invoice total stays 50, on the 13% tax only.
        self._assert_selected_lines_only(order, unselected, 44.25, 5.75, 50.0)
