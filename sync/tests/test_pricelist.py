from odoo.tests import TransactionCase
#from odoo.addons.sync.models import sync
from odoo.addons.sync.models import sync_pricelist

#To run the test, open the console and type : 
# odoo-bin --test-enable -i pricelist

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
        #self.sync_pricelist = sync_pricelist("CCP CSV_ODOO", self.pricelist_data, self.sync_model)

    def test_01(self):
         self.assertEqual(False, True)

