# -*- coding: utf-8 -*-
from odoo import Command
from odoo.tests import TransactionCase, tagged

_FLAGS = ('is_optional', 'is_selected', 'is_quantityLocked')


@tagged('post_install', '-at_install')
class TestOptionalFlagDefaults(TransactionCase):
    """Lines created without the proquotes boolean flags must still save.

    The flag columns are NOT NULL. Odoo's own create paths (down payment
    wizard, extra delivered lines, delivery and cart lines) never pass them,
    so the fields need default=False.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.partner = cls.env['res.partner'].create({
            'name': 'Optional Flag Defaults Customer',
            'is_company': True,
        })
        cls.product = cls.env['product.product'].create({
            'name': 'Optional Flag Defaults Product',
            'type': 'service',
            'invoice_policy': 'order',
            'list_price': 100.0,
            'taxes_id': [Command.clear()],
            'supplier_taxes_id': [Command.clear()],
        })
        cls.tax = cls.env['account.tax'].create({
            'name': 'Optional flag defaults HST 13%',
            'amount_type': 'percent',
            'amount': 13.0,
            'type_tax_use': 'sale',
            'price_include': False,
            'company_id': cls.company.id,
        })
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Optional flag defaults pricelist',
            'currency_id': cls.company.currency_id.id,
            'company_id': cls.company.id,
        })
        cls.header = cls.env['header.footer'].create({
            'name': 'Optional flag defaults header',
            'record_type': 'Header',
            'url': 'https://example.com/optional-flag-defaults-header.png',
        })
        cls.footer = cls.env['header.footer'].create({
            'name': 'Optional flag defaults footer',
            'record_type': 'Footer',
            'url': 'https://example.com/optional-flag-defaults-footer.png',
        })

    def _stored_flags(self, lines):
        """Read the raw column values, so NULL is not hidden as False."""
        lines.flush_recordset()
        self.env.cr.execute(
            'SELECT id, is_optional, is_selected, "is_quantityLocked" '
            'FROM sale_order_line WHERE id IN %s',
            (tuple(lines.ids),),
        )
        return {row[0]: row[1:] for row in self.env.cr.fetchall()}

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

    def _quote(self):
        order = self.env['sale.order'].create({
            'partner_id': self.partner.id,
            'pricelist_id': self.pricelist.id,
            'company_id': self.company.id,
            'header_id': self.header.id,
            'footer_id': self.footer.id,
            'order_line': [
                self._product_vals(1, 'Selected line', 100.0, True),
                self._product_vals(2, 'Unselected optional line', 50.0, False),
            ],
        })
        plan = {1: ('Selected line', 'true', 100.0), 2: ('Unselected optional line', 'false', 50.0)}
        for line in order.order_line:
            name, selected, price = plan[line.sequence]
            line.with_context(skip_apply_canadian_sales_taxes=True).write({
                'name': name,
                'selected': selected,
                'price_unit': price,
                'tax_id': [Command.set(self.tax.ids)],
            })
        return order

    def test_create_without_flags(self):
        order = self._quote()
        line = self.env['sale.order.line'].create({
            'order_id': order.id,
            'product_id': self.product.id,
            'name': 'Line created without proquotes flags',
            'product_uom_qty': 1.0,
        })
        self.assertEqual(self._stored_flags(line)[line.id], (False, False, False))

    def test_down_payment_on_confirmed_order_with_unselected_optional(self):
        order = self._quote()
        order.action_confirm()
        unselected = order.order_line.filtered(lambda l: l.name == 'Unselected optional line')

        wizard = self.env['sale.advance.payment.inv'].with_context(
            active_model='sale.order',
            active_ids=order.ids,
            active_id=order.id,
        ).create({
            'advance_payment_method': 'fixed',
            'fixed_amount': 50.0,
            'sale_order_ids': [Command.set(order.ids)],
        })
        wizard.create_invoices()

        down_payment_lines = order.order_line.filtered('is_downpayment')
        section = down_payment_lines.filtered(lambda l: l.display_type == 'line_section')
        payment = down_payment_lines - section
        self.assertEqual(len(section), 1)
        self.assertTrue(payment)
        self.assertTrue(order.invoice_ids)
        stored = self._stored_flags(down_payment_lines)
        for line in down_payment_lines:
            self.assertEqual(stored[line.id], (False, False, False))

        # The down payment must not make the unselected line invoiceable.
        self.assertEqual(unselected.qty_to_invoice, 0.0)
