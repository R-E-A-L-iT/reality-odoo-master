# -*- coding: utf-8 -*-
from datetime import timedelta

from odoo import Command, fields
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, tagged

# Columns the Customer Products list reads on each lot.
_LOT_DISPLAY_FIELDS = ["name", "sku", "product_id", "expire", "formated_label"]


@tagged("post_install", "-at_install")
class TestCustomerProductsCompanyAccess(TransactionCase):
    """Customer lot tabs must follow the company switcher.

    The Products tab still lists only lots in company 1 (the existing
    domain). Record rules then drop any of those lots whose company is
    not ticked. Reading the tab must not raise AccessError.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env["res.company"].browse(1)
        if not cls.company_a.exists():
            raise AssertionError("Company 1 is required for the customer products filter")
        cls.company_b = cls.env["res.company"].create({
            "name": "Products Access Company B",
            "currency_id": cls.company_a.currency_id.id,
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Owned Lots Partner",
            "is_company": True,
            "company_id": False,
            "company_nickname": "OWNEDLOTS",
        })
        cls.child = cls.env["res.partner"].create({
            "name": "Owned Lots Contact",
            "parent_id": cls.partner.id,
            "type": "contact",
            "company_id": False,
            "company_nickname": "_",
        })
        cls.product = cls.env["product.product"].create({
            "name": "Company Access Stock Product",
            "detailed_type": "product",
            "tracking": "serial",
            "company_id": False,
        })
        cls.lot = cls.env["stock.lot"].with_company(cls.company_a).create({
            "name": "test-lot-company-access",
            "product_id": cls.product.id,
            "company_id": cls.company_a.id,
            "owner": cls.partner.id,
        })
        cls.other_company_lot = cls.env["stock.lot"].with_company(cls.company_b).create({
            "name": "test-lot-other-company",
            "product_id": cls.product.id,
            "company_id": cls.company_b.id,
            "owner": cls.partner.id,
        })
        cls.pricelist = cls.env["product.pricelist"].create({
            "name": "Products access pricelist",
            "currency_id": cls.company_b.currency_id.id,
            "company_id": cls.company_b.id,
        })
        cls.header = cls.env["header.footer"].create({
            "name": "Products access header",
            "record_type": "Header",
            "url": "https://example.com/products-access-header.png",
        })
        cls.footer = cls.env["header.footer"].create({
            "name": "Products access footer",
            "record_type": "Footer",
            "url": "https://example.com/products-access-footer.png",
        })
        cls.user = cls.env["res.users"].create({
            "name": "Products Access User",
            "login": "products_access_user",
            "email": "products_access_user@example.com",
            "company_id": cls.company_b.id,
            "company_ids": [Command.set([cls.company_a.id, cls.company_b.id])],
            "groups_id": [Command.set([
                cls.env.ref("base.group_user").id,
                cls.env.ref("sales_team.group_sale_salesman_all_leads").id,
                cls.env.ref("stock.group_stock_user").id,
            ])],
        })
        order_vals = {
            "partner_id": cls.partner.id,
            "company_id": cls.company_b.id,
            "pricelist_id": cls.pricelist.id,
            "header_id": cls.header.id,
            "footer_id": cls.footer.id,
            "user_id": cls.user.id,
        }
        Order = cls.env["sale.order"].with_company(cls.company_b)
        cls.order = Order.create(dict(order_vals))
        cls.rental_order = Order.create(dict(order_vals, is_rental_order=True))

    def _lots(self, record, field_name, allowed_company_ids):
        """Read the tab the way the web client does, then its display columns."""
        self.env.invalidate_all()
        scoped = record.with_user(self.user).with_context(
            allowed_company_ids=list(allowed_company_ids),
        )
        payload = scoped.read([field_name])[0]
        lots = scoped.env["stock.lot"].browse(payload[field_name])
        if lots:
            lots.read(_LOT_DISPLAY_FIELDS)
        return lots

    def test_hidden_company_lots_are_not_readable_directly(self):
        self.env.invalidate_all()
        hidden = self.lot.with_user(self.user).with_context(
            allowed_company_ids=[self.company_b.id],
        )
        with self.assertRaises(AccessError):
            hidden.read(["name"])

    def test_unticked_company_lots_are_omitted_from_customer_tabs(self):
        only_b = [self.company_b.id]
        for record, field_name in (
            (self.order, "products"),
            (self.rental_order, "products"),
            (self.partner, "products"),
            (self.child, "products"),
            (self.child, "parentProducts"),
        ):
            lots = self._lots(record, field_name, only_b)
            self.assertNotIn(self.lot, lots)
            self.assertNotIn(self.other_company_lot, lots)

    def test_ticked_company_lots_are_shown(self):
        both = [self.company_a.id, self.company_b.id]
        for record, field_name in (
            (self.order, "products"),
            (self.rental_order, "products"),
            (self.partner, "products"),
            (self.child, "parentProducts"),
        ):
            lots = self._lots(record, field_name, both)
            self.assertIn(self.lot, lots)
            self.assertNotIn(self.other_company_lot, lots)
            shown = lots.filtered(lambda lot: lot == self.lot)
            self.assertEqual(shown.name, self.lot.name)
            self.assertIn(self.lot.name, shown.formated_label)

        child_lots = self._lots(self.child, "products", both)
        self.assertNotIn(self.lot, child_lots)

    def test_new_quote_for_that_customer_does_not_raise(self):
        only_b = [self.company_b.id]
        both = [self.company_a.id, self.company_b.id]
        Order = self.env["sale.order"].with_user(self.user).with_context(
            allowed_company_ids=only_b,
        )
        created = Order.create({
            "partner_id": self.partner.id,
            "company_id": self.company_b.id,
            "pricelist_id": self.pricelist.id,
            "header_id": self.header.id,
            "footer_id": self.footer.id,
            "user_id": self.user.id,
        })
        hidden = self._lots(created, "products", only_b)
        self.assertNotIn(self.lot, hidden)

        shown = self._lots(created, "products", both)
        self.assertIn(self.lot, shown)

        draft = self.env["sale.order"].with_user(self.user).with_context(
            allowed_company_ids=only_b,
        ).new({
            "partner_id": self.partner.id,
            "company_id": self.company_b.id,
            "pricelist_id": self.pricelist.id,
        })
        # new() stores x2many ids as NewId; compare the real records.
        picked = draft.products._origin
        self.assertNotIn(self.lot, picked)
        if picked:
            picked.read(_LOT_DISPLAY_FIELDS)

    def test_update_prices_does_not_read_hidden_company_lots(self):
        """Changing a rental end date and updating prices must not raise.

        The Customer Products tab is a different field. Update Prices
        follows the serials stored on the rental line. A stored compute
        loads those serials as superuser; reading ``name`` afterwards
        raises the lot multi-company rule. The price update has to finish,
        and the serial must stay linked without being shown.
        """
        only_b = [self.company_b.id]
        order = self.rental_order
        if "rent_ok" in self.product._fields:
            self.product.sudo().write({"rent_ok": True})
        start = fields.Datetime.now()
        end = start + timedelta(days=4)
        date_vals = {}
        if "rental_start_date" in order._fields:
            date_vals["rental_start_date"] = start
            date_vals["rental_return_date"] = end
        if date_vals:
            order.write(date_vals)
        order.write({
            "order_line": [Command.create({
                "product_id": self.product.id,
                "product_uom_qty": 1.0,
                "name": self.product.name,
                "price_unit": 10.0,
            })],
        })
        line = order.order_line.filtered(lambda item: item.product_id == self.product)[:1]
        self.assertTrue(line)
        lot_fields = [
            name for name in ("reserved_lot_ids", "pickedup_lot_ids", "returned_lot_ids")
            if name in line._fields
        ]
        for name in lot_fields:
            line.sudo().write({name: [Command.link(self.lot.id)]})

        user_line = line.with_user(self.user).with_context(allowed_company_ids=only_b)
        if lot_fields:
            # Same cache a stored superuser compute leaves behind.
            self.env.invalidate_all()
            line.sudo()[lot_fields[0]]
            with self.assertRaises(AccessError):
                user_line[lot_fields[0]].mapped("name")
            user_line._proquotes_drop_rental_lot_cache()
            self.assertNotIn(self.lot, user_line[lot_fields[0]])
            user_line[lot_fields[0]].mapped("name")

            self.env.invalidate_all()
            line.sudo()[lot_fields[0]]
        user_order = order.with_user(self.user).with_context(allowed_company_ids=only_b)
        user_order.action_update_prices()
        self.assertNotIn(self.lot, user_order.products)
        if lot_fields:
            self.assertNotIn(self.lot, user_line[lot_fields[0]])
            user_line[lot_fields[0]].mapped("name")
            self.env.invalidate_all()
            self.assertIn(self.lot, line.sudo()[lot_fields[0]])
            hidden = self._lots(line, lot_fields[0], only_b)
            self.assertNotIn(self.lot, hidden)

        if "return_date" in line._fields:
            if lot_fields:
                self.env.invalidate_all()
                line.sudo()[lot_fields[0]]
            user_line.write({"return_date": end + timedelta(days=2)})
            if lot_fields:
                self.assertNotIn(self.lot, user_line[lot_fields[0]])
                user_line[lot_fields[0]].mapped("name")
                self.env.invalidate_all()
                self.assertIn(self.lot, line.sudo()[lot_fields[0]])
