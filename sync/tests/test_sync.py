from odoo.tests import TransactionCase
from odoo.addons.sync.models import sync

#To run the test, open the console and type : 
# odoo-bin --test-enable -i sync


class TestModuleDemo(TransactionCase):

    #def setUp(self):
    #    super(TestModuleDemo, self).setUp()
            
    def test_is_psw_filled(self):
        synce_model = self.env['sync.sync']

        psw = {
            "key1": "value1",
            "key2": "value2"
        }

        result = synce_model.is_psw_filled(None)
        self.assertEqual(result, False)

        result = synce_model.is_psw_filled("password")
        self.assertEqual(result, False)

        result = synce_model.is_psw_filled(psw)
        self.assertEqual(result, True)

    
    def test_getSheetIndex(self):
    #def getSheetIndex(self, sync_data, lineIndex):
        synce_model = self.env['sync.sync']
        sync_data = [
            ['Sheet Name',      'Sheet Index',  'Model Type',   'Valid'], 
            ['Companies_',	    '10',           'Companies',    'TRUE'], 
            ['Contacts_',       '20',           'Contacts',     'TRUE'], 
            ['Pricelist-1_',    '30',           'Pricelist',    'TRUE'], 
            ['Pricelist-2_',    '40',           'Pricelist',    'TRUE'], 
            ['Products_',       '50',           'Products',     'TRUE'], 
            ['CCP_',            'sdf',          'CCP',          'TRUE'], 
            ['',                'Loading...',   '',             'FALSE'],
            ['',                'Loading...',   '',             'FALSE']
        ]
        result = synce_model.getSheetIndex(sync_data, 1)
        self.assertEqual(10, result)

        self.assertRaises(ValueError, synce_model.getSheetIndex, sync_data, 6)
           

