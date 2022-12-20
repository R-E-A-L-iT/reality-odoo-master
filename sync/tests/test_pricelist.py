from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync


#To run the test, open the console and type : 
# odoo-bin --test-enable -i sync

class TestModulePricelist(TransactionCase):

    def setUp(self):
        super(TestModulePricelist, self).setUp()
        self.pricelist_data = [
	        ['SKU', 'Description', 'Price CAD', 'Price USD', 'Product Type', 'Tracking', 'Valid', 'Continue'], 
	        [	'SKU-1111',	'Name of SKU-1111', 'Description  of SKU-1111', '111.11', '131.11', 'product', 'serial', 'TRUE', 'TRUE'], 		
	        [	'SKU-2222', 'Name of SKU-2222', 'Description  of SKU-2222', '222.22', '262.22', 'product', 'serial', 'TRUE', 'TRUE'],
	        [	'SKU-3333', 'Name of SKU-3333', 'Description  of SKU-3333', '333.33', '393.33', 'product', 'serial', 'TRUE', 'FALSE'],
	        [	'Not valid SKU', 'Not valid Name', 'Not valid Description', '-1', '-1', 'Not valid product', 'Not valid serial', 'FALSE', 'FALSE'],		
        ]     
        self.sync_model = self.env['sync.sync']
        self.sync_pricelist = self.sync_model.getSync_pricelist("TEST_DATA_ODOO", self.pricelist_data)
       
    #def addProductToPricelist(self, product, pricelistName, price): 
    def test_addProductToPricelist(self):
        external_id = "SKU-1234123"
        product_name = "New product"  
        product = self.sync_model.createProducts(external_id, product_name)

        pricelist = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "USD Pricelist")])
        self.assertEqual(len(pricelist) == 1, True)
       
        pricelist = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "CAN Pricelist")])
        self.assertEqual(len(pricelist) == 1, True)

        pricelist_id = pricelist[0].id
        pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        self.assertEqual((len(pricelist_item_ids) == 0), True)

        price = 5595.00
        self.sync_pricelist.addProductToPricelist(product, "CAN Pricelist", price)

        pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        self.assertEqual((len(pricelist_item_ids) == 1), True)

        



