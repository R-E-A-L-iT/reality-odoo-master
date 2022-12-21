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
            ['Products_',       '50',           'Products',     'TRUE'], 
            ['CCP_',            'sdf',          'CCP',          'TRUE'], 
            ['',                '',             '',             'FALSE'],
            ['',                'Loading...',   '',             'FALSE']
        ]
            
    #def is_psw_filled(self, psw):              
    def test_is_psw_filled(self):    
        psw = {
            "key1": "value1",
            "key2": "value2"
        }

        result = self.sync_model.is_psw_filled(None)
        self.assertEqual(result, False)

        result = self.sync_model.is_psw_filled("password")
        self.assertEqual(result, False)

        result = self.sync_model.is_psw_filled(psw)
        self.assertEqual(result, True)

    #def getSheetIndex(self, sync_data, lineIndex):
    def test_getSheetIndex(self):    
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 1)
        self.assertEqual(10, result)

        result, msg = self.sync_model.getSheetIndex(self.sync_data, 6)
        self.assertEqual(-1, result)

        result, msg = self.sync_model.getSheetIndex(self.sync_data, 7)
        self.assertEqual(-1, result)
           
    #def createProducts(self, external_id, product_name):
    def test_createProducts(self):
        external_id = "SKU-1234123"
        product_name = "New product"  

        product_unexsiting = self.env['product.template'].search(
            [('sku', '=', external_id)])      
        self.assertEqual((len(product_unexsiting) == 0), True)

        product = self.sync_model.createProducts(external_id, product_name)
        product_exsiting = self.env['product.template'].search(
            [('sku', '=', product.sku)])
        self.assertEqual((len(product_exsiting) == 0), False)

    def test_updateProducts(self):
    #def updateProducts(
    #   self, 
    #   product, 
    #   product_stringRep, 
    #   product_name, 
    #   product_description_sale, 
    #   product_price_cad, 
    #   product_price_usd,
    #   product_tracking,
    #   product_type):

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

        self.assertEqual((product_not_updated.sku == external_id), True)
        self.assertEqual((product_not_updated.name == product_name), True)
        self.assertEqual((product_not_updated.stringRep == product_stringRep), False)
        self.assertEqual((product_not_updated.description_sale == product_description_sale), False)
        self.assertEqual((product_not_updated.price == product_price_cad), False)
        self.assertEqual((product_not_updated.tracking == product_tracking), True)
        self.assertEqual((product_not_updated.type == product_type), True)

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

        self.sync_model.updateProducts(
            product, 
            product_stringRep, 
            product_name, 
            product_description_sale, 
            product_price_cad, 
            product_price_usd,
            product_tracking,
            product_type)



        product_updated = self.env['product.template'].search(
            [('id', '=', product.id)])

        print("TEST")
        print ("product_updated.price: " + str(product_updated.price))
        print ("product_price_cad: " + str(product_price_cad))


        self.assertEqual((product_updated.sku == external_id), True)
        self.assertEqual((product_updated.name == product_name), True)
        self.assertEqual((product_updated.stringRep == product_stringRep), True)
        self.assertEqual((product_updated.description_sale == product_description_sale), True)
        self.assertEqual((str(product_updated.price) == str(product_price_cad)), True)        
        self.assertEqual((product_updated.tracking == product_tracking), True)
        self.assertEqual((product_updated.type == product_type), True)

        #pricelist = self.sync_model.env['product.pricelist'].search(
        #    [('name', '=', "CAN Pricelist")])            
        #pricelist_id = pricelist[0].id
        #pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
        #    [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        #self.assertEqual((len(pricelist_item_ids) == 1), True)
        #
        #pricelist = self.sync_model.env['product.pricelist'].search(
        #    [('name', '=', "USD Pricelist")])            
        #pricelist_id = pricelist[0].id
        #pricelist_item_ids = self.sync_model.env['product.pricelist.item'].search(
        #    [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        #self.assertEqual((len(pricelist_item_ids) == 1), True)










            

    #def archive_product(self, product_id):
    def test_archive_product(self):
        external_id = "SKU-1234123"
        product_name = "New product"        
        product = self.sync_model.createProducts(external_id, product_name)

        self.sync_model.archive_product(str(product.id))

        product_modified = self.env['product.template'].search(
            [('id', '=', product.id)]
        )
        self.assertEqual(product_modified.active, False)
      
    #def getColumnIndex (self, sheet, columnName):
    def test_getColumnIndex (self):
        result = self.sync_model.getColumnIndex(self.sync_data, "Sheet Index")
        self.assertEqual((result == 1), True)

        result = self.sync_model.getColumnIndex(self.sync_data, "Does not exists")
        self.assertEqual((result == -1), True) 





