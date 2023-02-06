from odoo.tests import TransactionCase
from odoo.addons.sync.models.pricelist import sync_pricelist

# To run the test, open the console and type :
# odoo-bin --test-enable -i sync


class TestModulePricelist(TransactionCase):

    def setUp(self):
        super(TestModulePricelist, self).setUp()
        self.pricelist_data = [
            ['SKU', 'Description', 'Price CAD', 'Price USD',
                'Product Type', 'Tracking', 'Valid', 'Continue'],
            ['SKU-1111',	'Name of SKU-1111', 'Description  of SKU-1111',
                '111.11', '131.11', 'product', 'serial', 'TRUE', 'TRUE'],
            ['SKU-2222', 'Name of SKU-2222', 'Description  of SKU-2222',
             '222.22', '262.22', 'product', 'serial', 'TRUE', 'TRUE'],
            ['SKU-3333', 'Name of SKU-3333', 'Description  of SKU-3333',
             '333.33', '393.33', 'product', 'serial', 'TRUE', 'FALSE'],
            ['Not valid SKU', 'Not valid Name', 'Not valid Description', '-1',
                '-1', 'Not valid product', 'Not valid serial', 'FALSE', 'FALSE'],
        ]
        self.sync_model = self.env['sync.sync']
        self.sync_pricelist = sync_pricelist(
            "Test Sheet", self.pricelist_data, self.sync_model)

    # def addProductToPricelist(self, product, pricelistName, price):

    def test_addProductToPricelist(self):
        external_id = "SKU-1234123"
        product_name = "New product"
        price = 5595.00
        product = self.sync_model.createProducts(external_id, product_name)

        # Assert that "USD Pricelist" is unique as a pricelist name
        pricelist_usd = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "USD Pricelist")])
        self.assertEqual(len(pricelist_usd) == 1, True)

        # Assert that "CAN Pricelist" is unique as a pricelist name
        pricelist_can = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "CAN Pricelist")])
        self.assertEqual(len(pricelist_can) == 1, True)

        # Assert that the product.id doest not exist in the 'CAN pricelist'
        pricelist_can_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_can.id)])
        self.assertEqual((len(pricelist_can_item_ids) == 0), True)

        # Calling the method to test
        self.sync_pricelist.addProductToPricelist(
            product, "CAN Pricelist", price)

        # Assert that their is only one price.
        pricelist_can_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_can.id)])
        self.assertEqual((len(pricelist_can_item_ids) == 1), True)

        # Assert that the price is not introduc in an other pricelist
        pricelist_usd_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=',  pricelist_usd.id)])
        self.assertEqual((len(pricelist_usd_item_ids) == 0), True)
