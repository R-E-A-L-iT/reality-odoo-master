from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync

#To run the test, open the console and type : 
# odoo-bin --test-enable -i sync


class TestModuleSync(TransactionCase):

    def setUp(self):
        super(TestModuleSync, self).setUp()
        self.sync_model = self.env['sync.sync']
        self.sync_data = [
            ['Sheet Name',      'Sheet Index',  'Model Type',   'Valid'], 
            ['Companies_',	    '10',           'Companies',    'TRUE'], 
            ['Contacts_',       '20',           'Contacts',     'TRUE'], 
            ['Pricelist-1_',    '30',           'Pricelist',    'TRUE'], 
            ['Pricelist-2_',    '40',           'Pricelist',    'TRUE'], 
            ['Products_',       '50.1',         'Products',     'TRUE'], 
            ['CCP_',            'sdf',          'CCP',          'TRUE'], 
            ['',                '',             '',             'FALSE'],
            ['',                'Loading...',   '',             'FALSE']
        ]

        self.sync_data_order_changed = [
            ['Sheet Name',      'Model Type',   'Valid', 'Sheet Index'], 
            ['Companies_',	    '11',           'TRUE' , '10'         ], 
            ['Contacts_',       '21',           'TRUE' , '20'         ], 
            ['Pricelist-1_',    '31',           'TRUE' , '30'         ], 
            ['Pricelist-2_',    '41',           'TRUE' , '40'         ], 
            ['Products_',       '51.1',         'TRUE' , '50.1'       ], 
            ['CCP_',            '60',           'TRUE' , 'sdf'        ], 
            ['',                '',             'FALSE', ''           ],
            ['',                '',             'FALSE', 'Loading...' ]
        ]
            
    #def is_psw_format_good(self, psw):              
    def test_is_psw_format_good(self):    
        psw = {
            "key1": "value1",
            "key2": "value2"
        }

        #Assert that with no passware, it return False.
        result = self.sync_model.is_psw_format_good(None)
        self.assertEqual(result, False)

        #Assert that passing a password in a string, it return False.
        result = self.sync_model.is_psw_format_good("Password")
        self.assertEqual(result, False)

        #Assert that with dictionnary, it return True.
        #Note that we are not testing if the password is valid or not, but the format
        result = self.sync_model.is_psw_format_good(psw)
        self.assertEqual(result, True)


    #def getSheetIndex(self, sync_data, lineIndex):
    def test_getSheetIndex(self):    
        #Assert that it return the right is value
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 1)
        self.assertEqual(10, result)

        #Assert that it return -1 is the value is a float
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 5)
        self.assertEqual(-1, result)

        #Assert that it return -1 is the value is a string
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 6)
        self.assertEqual(-1, result)        

        #Assert that it return -1 is the value is an empty string
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 7)
        self.assertEqual(-1, result)

        #Same asserts, but check that we can change the order of the tab and it will still work
        result, msg = self.sync_model.getSheetIndex(self.sync_data_order_changed, 1)
        self.assertEqual(10, result)
        result, msg = self.sync_model.getSheetIndex(self.sync_data_order_changed, 5)
        self.assertEqual(-1, result)        
        result, msg = self.sync_model.getSheetIndex(self.sync_data_order_changed, 6)
        self.assertEqual(-1, result)
        result, msg = self.sync_model.getSheetIndex(self.sync_data_order_changed, 7)
        self.assertEqual(-1, result)
   
    #Test to be executer befor creating a product
    #Input
    #   external_id: Sku to check if not existing
    def pretest_createProducts(self, external_id):
        #Assert that the product to be created does not exist to validate the test.
        product_unexsiting = self.env['product.template'].search(
            [('sku', '=', external_id)])      
        self.assertEqual((len(product_unexsiting) == 0), True)

    #def createProducts(self, external_id, product_name):
    def test_createProducts(self):
        external_id = "SKU-1234123"
        product_name = "New product"  

        self.pretest_createProducts(external_id)

        #Calling the methode to test
        product = self.sync_model.createProducts(external_id, product_name)

        #Assert that if a product is created, it their is only on SKU with this value
        product_exsiting = self.env['product.template'].search(
            [('sku', '=', product.sku)])
        self.assertEqual((len(product_exsiting) == 1), True)

    
    #Test to be done after a product update
    def aftertest_updateProducts(
        self, 
        product_id, 
        external_id, 
        product_name, 
        product_stringRep, 
        product_description_sale, 
        product_price_cad, 
        product_tracking, 
        product_type):

        #Assert that if a product is created, the SKU is unique
        product_updated = self.env['product.template'].search(
            [('sku', '=', external_id)])
        self.assertEqual((len(product_updated) == 1), True)   

        #Assert that if a product is created, the ID is unique
        product_updated = self.env['product.template'].search(
            [('id', '=', product_id)])
        self.assertEqual((len(product_updated) == 1), True)

        #Assert that all the test data is properly set in the updated product
        self.assertEqual((product_updated.sku == external_id), True)
        self.assertEqual((product_updated.name == product_name), True)
        self.assertEqual((product_updated.stringRep == product_stringRep), True)
        self.assertEqual((product_updated.description_sale == product_description_sale), True)
        self.assertEqual((str(float(product_updated.price)) == str(float(product_price_cad))), True)        
        self.assertEqual((product_updated.tracking == product_tracking), True)
        self.assertEqual((product_updated.type == product_type), True)

        #Assert that there is only one price per product in 'CAN pricelist' and 'USD pricelist'
        pricelist_can = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "CAN Pricelist")])            
        self.assertEqual(len(pricelist_can) == 1, True)
        pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product_id), ('pricelist_id', '=', pricelist_can.id)])
        self.assertEqual((len(pricelist_item_ids) == 1), True)
        
        pricelist_usd = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "USD Pricelist")])            
        self.assertEqual(len(pricelist_usd) == 1, True)
        pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product_id), ('pricelist_id', '=', pricelist_usd.id)])
        self.assertEqual((len(pricelist_item_ids) == 1), True)        

    #def updateProducts(
    #       self, 
    #       product, 
    #       product_stringRep, 
    #       product_name, 
    #       product_description_sale, 
    #       product_price_cad, 
    #       product_price_usd,
    #       product_tracking,
    #       product_type):
    def test_updateProducts(self):        
        external_id                 = "SKU-123456"
        product_stringRep           = "['SKU-123456', 'Name of the product', 'Description of the product', '3850', '2980', 'Product Type of the product', 'Tracking of the product', 'TRUE', 'TRUE']"
        product_name                = "Name of the product" 
        product_description_sale    = "Description of the product"
        product_price_cad           = "3850"
        product_price_usd           = "2980"
        product_tracking            = "serial"
        product_type                = "product"

        product = self.sync_model.createProducts(external_id, product_name)
        product_not_updated = self.env['product.template'].search(
            [('id', '=', product.id)])

        #Assert that the product created match the tests values.
        self.assertEqual((product_not_updated.sku == external_id), True)
        self.assertEqual((product_not_updated.name == product_name), True)
        self.assertEqual((product_not_updated.tracking == product_tracking), True)
        self.assertEqual((product_not_updated.type == product_type), True)

        #Validate that the test value are not set before the method is executed.
        self.assertEqual((product_not_updated.stringRep == product_stringRep), False)
        self.assertEqual((product_not_updated.description_sale == product_description_sale), False)
        self.assertEqual((product_not_updated.price == product_price_cad), False)
 
        #Assert that the 'CAN pricelist' and 'USD priclist' doest not contain information on the product.
        pricelist = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "CAN Pricelist")])            
        pricelist_id = pricelist[0].id
        pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        self.assertEqual((len(pricelist_item_ids) == 0), True)
        
        pricelist = self.sync_model.env['product.pricelist'].search(
            [('name', '=', "USD Pricelist")])            
        pricelist_id = pricelist[0].id
        pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        self.assertEqual((len(pricelist_item_ids) == 0), True)

        #calling the method to test
        self.sync_model.updateProducts(
            product, 
            product_stringRep, 
            product_name, 
            product_description_sale, 
            product_price_cad, 
            product_price_usd,
            product_tracking,
            product_type)

        self.aftertest_updateProducts(
            self, 
            product.id, 
            external_id, 
            product_name, 
            product_stringRep, 
            product_description_sale, 
            product_price_cad, 
            product_tracking, 
            product_type)


    #def createAndUpdateProducts(
    #        self, 
    #        external_id, 
    #        product_stringRep, 
    #        product_name, 
    #        product_description_sale, 
    #        product_price_cad, 
    #        product_price_usd,
    #        product_tracking,
    #        product_type):
    def test_createAndUpdateProducts(self):
        external_id                 = "SKU-123456"
        product_stringRep           = "['SKU-123456', 'Name of the product', 'Description of the product', '3850', '2980', 'Product Type of the product', 'Tracking of the product', 'TRUE', 'TRUE']"
        product_name                = "Name of the product" 
        product_description_sale    = "Description of the product"
        product_price_cad           = "3850"
        product_price_usd           = "2980"
        product_tracking            = "serial"
        product_type                = "product"

        self.pretest_createProducts(external_id)

        #Callind the method
        product = self.createAndUpdateProducts(
            external_id, 
            product_stringRep, 
            product_name, 
            product_description_sale, 
            product_price_cad, 
            product_price_usd,
            product_tracking,
            product_type)

        self.aftertest_updateProducts(
            product.id, 
            external_id, 
            product_name, 
            product_stringRep, 
            product_description_sale, 
            product_price_cad, 
            product_tracking, 
            product_type)


    #def archive_product(self, product_id):
    def test_archive_product(self):
        external_id = "SKU-1234123"
        product_name = "New product"        
        product = self.sync_model.createProducts(external_id, product_name)

        #Validate that the product to archived is active before calling the method
        self.assertEqual(product.active, True)

        #calling the method
        self.sync_model.archive_product(str(product.id))

        product_modified = self.env['product.template'].search(
            [('id', '=', product.id)])
        #Assert that once archived, it is not active.
        self.assertEqual(product_modified.active, False)

      
    #def getColumnIndex (self, sheet, columnName):
    def test_getColumnIndex (self):
        #Assert that the method return the good data
        result = self.sync_model.getColumnIndex(self.sync_data, "Sheet Index")
        self.assertEqual((result == 1), True)

        #Assert that the method return -1 when column does not exist
        result = self.sync_model.getColumnIndex(self.sync_data, "Does not exists")
        self.assertEqual((result == -1), True) 





