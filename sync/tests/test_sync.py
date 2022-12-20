from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync

#To run the test, open the console and type : 
# odoo-bin --test-enable -i sync


class TestModuleDemo(TransactionCase):

    def setUp(self):
        super(TestModuleDemo, self).setUp()
        self.synce_model = self.env['sync.sync']
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
        #synce_model = self.env['sync.sync']

        psw = {
            "key1": "value1",
            "key2": "value2"
        }

        result = self.synce_model.is_psw_filled(None)
        self.assertEqual(result, False)

        result = self.synce_model.is_psw_filled("password")
        self.assertEqual(result, False)

        result = self.synce_model.is_psw_filled(psw)
        self.assertEqual(result, True)

        self.sync_data = []
        

    #def getSheetIndex(self, sync_data, lineIndex):
    def test_getSheetIndex(self):    
        #synce_model = self.env['sync.sync']

        result, msg = self.synce_model.getSheetIndex(self.sync_data, 1)
        self.assertEqual(10, result)

        result, msg = self.synce_model.getSheetIndex(self.sync_data, 6)
        self.assertEqual(-1, result)

        result, msg = self.synce_model.getSheetIndex(self.sync_data, 7)
        self.assertEqual(-1, result)
           

    #def archive_product(self, product_id):
    #def test_archive_product(self):
    #    pass

