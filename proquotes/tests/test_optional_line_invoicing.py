# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestOptionalLineInvoicing(TransactionCase):
    """Unselected optional lines must not be invoiced on a confirmed order."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'Optional Line Invoicing Customer',
            'is_company': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Optional Line Invoicing Product',
            'type': 'service',
            'invoice_policy': 'order',
            'list_price': 100.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })
        cls.tax = cls.env['account.tax'].create({
            'name': 'Optional line invoicing HST 13%',
            'amount_type': 'percent',
            'amount': 13.0,
            'type_tax_use': 'sale',
            'price_include': False,
            'company_id': cls.company.id,
        })
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Optional line invoicing pricelist',
            'currency_id': cls.company.currency_id.id,
            'company_id': cls.company.id,
        })
        cls.header = cls.env['header.footer'].create({
            'name': 'Optional line invoicing header',
            'record_type': 'Header',
            'url': 'https://example.com/optional-line-invoicing-header.png',
        })
        cls.footer = cls.env['header.footer'].create({
            'name': 'Optional line invoicing footer',
            'record_type': 'Footer',
            'url': 'https://example.com/optional-line-invoicing-footer.png',
        })

    def _product_vals(self, sequence, name, price, selected):
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
            'tax_id': [Command.set(self.tax.ids)],
        })

    def _section_vals(self, sequence, name, selected):
        return Command.create({
            'sequence': sequence,
            'display_type': 'line_section',
            'name': name,
            'selected': 'true' if selected else 'false',
            'is_selected': selected,
            'optional': 'no',
            'is_optional': False,
            'is_quantityLocked': True,
        })

    def _create_quote(self, line_commands, plan):
        """Create a quote with no template, then re-pin price, tax, and selected.

        sale.order.create turns Canadian tax automation back on, and creating
        a line can replace the unit price and the description with the product
        list price and sales description. Lines are matched by sequence, which
        those onchanges do not rewrite. Header and footer are required.
        """
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
            'company_id': self.company.id,
            'header_id': self.header.id,
            'footer_id': self.footer.id,
            'order_line': line_commands,
        })
        self.assertEqual(len(order.order_line), len(plan))
        for line in order.order_line:
            spec = plan[line.sequence]
            vals = {
                'name': spec['name'],
                'selected': 'true' if spec['selected'] else 'false',
            }
            if not line.display_type:
                vals.update({
                    'price_unit': spec['price'],
                    'tax_id': [Command.set(self.tax.ids)],
                })
            line.with_context(skip_apply_canadian_sales_taxes=True).write(vals)
        return order

    def _standard_quote(self):
        return self._create_quote([
            self._product_vals(1, 'Selected line', 100.0, True),
            self._product_vals(2, 'Unselected optional line', 50.0, False),
        ], {
            1: {'name': 'Selected line', 'selected': True, 'price': 100.0},
            2: {'name': 'Unselected optional line', 'selected': False, 'price': 50.0},
        })

    def _product_invoice_lines(self, invoice):
        return invoice.invoice_line_ids.filtered(
            lambda line: line.display_type not in ('line_section', 'line_note')
        )

    def test_unselected_line_not_invoiced(self):
        order = self._standard_quote()
        order.action_confirm()
        selected = order.order_line.filtered(lambda line: line.name == 'Selected line')
        unselected = order.order_line.filtered(lambda line: line.name == 'Unselected optional line')

        self.assertEqual(unselected.qty_to_invoice, 0.0)
        self.assertEqual(unselected.untaxed_amount_to_invoice, 0.0)
        self.assertEqual(unselected.invoice_status, 'no')
        self.assertEqual(selected.qty_to_invoice, 1.0)
        self.assertEqual(selected.invoice_status, 'to invoice')
        self.assertEqual(order.invoice_status, 'to invoice')

        invoice = order._create_invoices()
        product_lines = self._product_invoice_lines(invoice)
        self.assertEqual(len(product_lines), 1)
        self.assertEqual(product_lines.sale_line_ids, selected)
        self.assertAlmostEqual(invoice.amount_untaxed, 100.0, places=2)
        self.assertAlmostEqual(invoice.amount_tax, 13.0, places=2)

        invoice.action_post()
        self.assertEqual(selected.invoice_status, 'invoiced')
        self.assertEqual(order.invoice_status, 'invoiced')

    def test_stale_stored_values(self):
        order = self._standard_quote()
        order.action_confirm()
        selected = order.order_line.filtered(lambda line: line.name == 'Selected line')
        unselected = order.order_line.filtered(lambda line: line.name == 'Unselected optional line')

        # Flush first. invalidate_model() writes pending stored computes, and
        # that would put the new zeros back over this simulated production row.
        line_model = self.env['sale.order.line']
        line_model.flush_model([
            'qty_to_invoice',
            'untaxed_amount_to_invoice',
            'invoice_status',
        ])
        self.env.cr.execute(
            """
            UPDATE sale_order_line
               SET qty_to_invoice = 1,
                   untaxed_amount_to_invoice = 50,
                   invoice_status = 'to invoice'
             WHERE id = %s
            """,
            [unselected.id],
        )
        line_model.invalidate_model()
        self.assertEqual(unselected.qty_to_invoice, 1.0)
        self.assertEqual(unselected.invoice_status, 'to invoice')

        invoiceable = order._get_invoiceable_lines()
        self.assertNotIn(unselected, invoiceable)
        self.assertIn(selected, invoiceable)

        invoice = order._create_invoices()
        product_lines = self._product_invoice_lines(invoice)
        self.assertEqual(len(product_lines), 1)
        self.assertEqual(product_lines.sale_line_ids, selected)

    def test_sections(self):
        order = self._create_quote([
            self._section_vals(1, 'Section A', True),
            self._product_vals(2, 'Selected line', 100.0, True),
            self._section_vals(3, 'Section B', False),
            self._product_vals(4, 'Unselected optional line', 50.0, False),
        ], {
            1: {'name': 'Section A', 'selected': True, 'price': 0.0},
            2: {'name': 'Selected line', 'selected': True, 'price': 100.0},
            3: {'name': 'Section B', 'selected': False, 'price': 0.0},
            4: {'name': 'Unselected optional line', 'selected': False, 'price': 50.0},
        })
        order.action_confirm()
        section_a = order.order_line.filtered(lambda line: line.name == 'Section A')
        section_b = order.order_line.filtered(lambda line: line.name == 'Section B')
        selected = order.order_line.filtered(lambda line: line.name == 'Selected line')
        unselected = order.order_line.filtered(lambda line: line.name == 'Unselected optional line')
        self.assertEqual(section_b.selected, 'false')

        invoice = order._create_invoices()
        sections = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type == 'line_section'
        )
        product_lines = self._product_invoice_lines(invoice)
        self.assertEqual(sections.mapped('name'), ['Section A'])
        self.assertEqual(product_lines.sale_line_ids, selected)
        self.assertIn(section_a, invoice.invoice_line_ids.sale_line_ids)
        self.assertNotIn(section_b, invoice.invoice_line_ids.sale_line_ids)
        self.assertNotIn(unselected, invoice.invoice_line_ids.sale_line_ids)

    def test_reselect_after_confirm(self):
        order = self._standard_quote()
        order.action_confirm()
        unselected = order.order_line.filtered(lambda line: line.name == 'Unselected optional line')
        unselected.write({'selected': 'true'})

        self.assertEqual(unselected.qty_to_invoice, 1.0)
        self.assertEqual(unselected.invoice_status, 'to invoice')

        invoice = order._create_invoices()
        self.assertIn(unselected, invoice.invoice_line_ids.sale_line_ids)

    def test_guard_keeps_refunds_and_sections(self):
        order = self._create_quote([
            self._section_vals(1, 'Section B', False),
            self._product_vals(2, 'Selected line', 100.0, True),
            self._product_vals(3, 'Unselected optional line', 50.0, False),
        ], {
            1: {'name': 'Section B', 'selected': False, 'price': 0.0},
            2: {'name': 'Selected line', 'selected': True, 'price': 100.0},
            3: {'name': 'Unselected optional line', 'selected': False, 'price': 50.0},
        })
        section = order.order_line.filtered(lambda line: line.name == 'Section B')
        selected = order.order_line.filtered(lambda line: line.name == 'Selected line')
        unselected = order.order_line.filtered(lambda line: line.name == 'Unselected optional line')
        self.assertEqual(section.selected, 'false')
        self.assertTrue(unselected._proquotes_is_unselected_product_line())

        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner.id,
            'footer_id': self.footer.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product.id,
                'name': 'Credit unselected line',
                'quantity': 1.0,
                'price_unit': 50.0,
                'sale_line_ids': [Command.set(unselected.ids)],
            })],
        })
        self.assertEqual(refund.state, 'draft')
        self.assertEqual(len(refund.invoice_line_ids), 1)
        self.assertEqual(refund.invoice_line_ids.sale_line_ids, unselected)

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner.id,
            'footer_id': self.footer.id,
            'invoice_line_ids': [
                Command.create({
                    'display_type': 'line_section',
                    'name': 'Section B',
                    'sale_line_ids': [Command.set(section.ids)],
                }),
                Command.create({
                    'product_id': self.product.id,
                    'name': 'Selected line',
                    'quantity': 1.0,
                    'price_unit': 100.0,
                    'tax_ids': [Command.set(self.tax.ids)],
                    'sale_line_ids': [Command.set(selected.ids)],
                }),
            ],
        })
        self.assertEqual(invoice.state, 'draft')
        self.assertEqual(len(invoice.invoice_line_ids), 2)
        section_lines = invoice.invoice_line_ids.filtered(
            lambda line: line.display_type == 'line_section'
        )
        product_lines = self._product_invoice_lines(invoice)
        self.assertEqual(len(section_lines), 1)
        self.assertEqual(section_lines.sale_line_ids, section)
        self.assertEqual(product_lines.sale_line_ids, selected)
