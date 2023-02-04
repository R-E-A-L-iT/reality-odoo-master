from odoo.tests import TransactionCase

# To run the test, open the console and type :
# odoo-bin --test-enable -i sync


class TestModuleSync(TransactionCase):

    def setUp(self):
        super(TestModuleSync, self).setUp()
        self.sync_model = self.env['sync.sync']
        self.sync_data = [
            ['Sheet Name',      'Sheet Index',
                'Model Type',   'Valid', 'Continue'],
            ['Companies_',	    '10',           'Companies',    'TRUE', 'TRUE'],
            ['Contacts_',       '20',           'Contacts',     'TRUE', 'TRUE'],
            ['Pricelist-1_',    '30',           'Pricelist',    'TRUE', 'TRUE'],
            ['CCP_-1_',         '40',           'CCP',          'TRUE', 'TRUE'],
            ['Products_',       '50.1',         'Products',     'TRUE', 'TRUE'],
            ['CCP_-2_',         'sdf',          'CCP',          'TRUE', 'TRUE'],
            ['',                '',             '',             'FALSE', 'FALSE'],
            ['',                'Loading...',   '',             'FALSE', 'FALSE']
        ]

        self.sync_data_order_changed = [
            ['Sheet Name',      'Model Type',   'Valid', 'Sheet Index', 'Continue'],
            ['Companies_',	    '11',           'TRUE', '10', 'TRUE'],
            ['Contacts_',       '21',           'TRUE', '20', 'TRUE'],
            ['Pricelist-1_',    '31',           'TRUE', '30', 'TRUE'],
            ['CCP_-1_',         '41',           'TRUE', '40', 'TRUE'],
            ['Products_',       '51.1',         'TRUE', '50.1', 'TRUE'],
            ['CCP_-2_',         '60',           'TRUE', 'sdf', 'TRUE'],
            ['',                '',             'FALSE', '', 'FALSE'],
            ['',                '',             'FALSE', 'Loading...', 'FALSE']
        ]

        self.sheet_index_30 = [
            ['SKU', 	 'EN-Name', 	 'EN-Description', 		'FR-Name', 		'FR-Description', 	   'Price CAD', 'Price USD', 'Can Rental', 'US Rental', 'Store Image', 								   'Store Title', 	   'Store Description', 	 'Publish_CA', 'Publish_USA', 'Can_Be_Sold',
                'E-Commerce_Website_Code', 'isSoftware', 'Product Type', 'Tracking', 'CAN PL SEL',    'CAN PL ID', 'USD PL SEL',    'US PL ID', 'CAN R SEL',  'CAN R ID', 	 'US R SEL',   'ECOM-FOLDER', 'ECOM-MEDIA', 'US R ID',   'Valid', 'Continue'],
            ['SKU-1111', 'EN-Name-1111', 'EN-Description-1111', 'FR-Name-1111',	'FR-Description-1111', '', 		 	'', 		 '0.5', 		'0.25', 	'https://r-e-a-l.it/images/products/1111.png', 'Store Title-1111', 'Store Description-1111', 'FALSE',
                'FALSE', 	  'TRUE', 	     '',   					    'FALSE',	  'product',      'serial',   'CAN Pricelist', 'CAN162200', 'USD Pricelist', 'US372200', 'CAN RENTAL', 'CANR939200', 'USD RENTAL', 'Leica', 	  '', 		    'USR127290', 'TRUE',  'TRUE'],
            ['SKU-1112', 'EN-Name-1112', 'EN-Description-1112', 'FR-Name-1112',	'FR-Description-1112', '330', 		'255', 	  	 '', 			'', 		'https://r-e-a-l.it/images/products/1112.png', 'Store Title-1112', 'Store Description-1112', 'FALSE',
                'FALSE', 	  'TRUE', 	     '',   					    'FALSE',	  'product',      'serial',   'CAN Pricelist', 'CAN165500', 'USD Pricelist', 'US375500', 'CAN RENTAL', 'CANR989500', 'USD RENTAL', 'Leica', 	  '', 		    'USR127590', 'TRUE',  'TRUE'],
            ['SKU-1113', 'EN-Name-1113', 'EN-Description-1113', 'FR-Name-1113',	'FR-Description-1113', '580', 		'450', 	  	 '29', 			'22.5', 	'https://r-e-a-l.it/images/products/1113.png', 'Store Title-1113', 'Store Description-1113', 'FALSE',
                'FALSE', 	  'TRUE', 	     '',   					    'FALSE',	  'product',      'serial',   'CAN Pricelist', 'CAN164752', 'USD Pricelist', 'US374752', 'CAN RENTAL', 'CANR999752', 'USD RENTAL', 'Leica', 	  '', 		    'USR127792', 'TRUE',  'TRUE']
        ]

        self.sheet_index_40 = [
            ['SKU', 	 'EN-Name', 	 'EN-Description', 		'FR-Name', 		'FR-Description', 	   'Price CAD', 'Price USD', 'Can Rental', 'US Rental', 'Store Image', 								   'Store Title', 	   'Store Description', 	 'Publish_CA', 'Publish_USA', 'Can_Be_Sold',
                'E-Commerce_Website_Code', 'isSoftware', 'Product Type', 'Tracking', 'CAN PL SEL',    'CAN PL ID', 'USD PL SEL',    'US PL ID',   'CAN R SEL',  'CAN R ID',   'US R SEL',   'ECOM-FOLDER', 'ECOM-MEDIA', 'US R ID',   'Valid', 'Continue'],
            ['SKU-2221', 'EN-Name-2221', 'EN-Description-2221', 'FR-Name-2221',	'FR-Description-2221', '', 		 	'', 		 '2.5', 		'1.25', 	'https://r-e-a-l.it/images/products/2221.png', 'Store Title-2221', 'Store Description-2221', 'FALSE',
                'FALSE', 	  'TRUE', 	     '',   					    'FALSE',	  'product',      'serial',   'CAN Pricelist', 'CAN33780',  'USD Pricelist', 'US389200',   'CAN RENTAL', 'CANR132290', 'USD RENTAL', 'Leica', 	    '', 		  'USR378907', 'TRUE',  'TRUE'],
            ['SKU-2222', 'EN-Name-2222', 'EN-Description-2222', 'FR-Name-2222',	'FR-Description-2222', '850', 		'1105',	  	 '', 			'', 		'https://r-e-a-l.it/images/products/2222.png', 'Store Title-2222', 'Store Description-2222', 'FALSE',
                'FALSE', 	  'TRUE', 	     '',   					    'FALSE',	  'product',      'serial',   'CAN Pricelist', 'CAN38780',  'USD Pricelist', 'US389500',   'CAN RENTAL', 'CANR185590', 'USD RENTAL', 'Leica', 	    '', 		  'USR378907', 'TRUE',  'TRUE'],
            ['SKU-2223', 'EN-Name-2223', 'EN-Description-2223', 'FR-Name-2223',	'FR-Description-2223', '695', 		'905', 	  	 '58', 			'75.5', 	'https://r-e-a-l.it/images/products/2223.png', 'Store Title-2223', 'Store Description-2223', 'FALSE',
                'FALSE', 	  'TRUE', 	     '',   					    'FALSE',	  'product',      'serial',   'CAN Pricelist', 'CAN39782',  'USD Pricelist', 'US389452',   'CAN RENTAL', 'CANR194792', 'USD RENTAL', 'Leica', 	    '', 		  'USR378957', 'TRUE',  'TRUE']
        ]

    # def is_psw_format_good(self, psw):

    def test_is_psw_format_good(self):
        psw = {
            "key1": "value1",
            "key2": "value2"
        }

        # Assert that with no passware, it return False.
        result = self.sync_model.is_psw_format_good(None)
        self.assertEqual(result, False)

        # Assert that passing a password in a string, it return False.
        result = self.sync_model.is_psw_format_good("Password")
        self.assertEqual(result, False)

        # Assert that with dictionnary, it return True.
        # Note that we are not testing if the password is valid or not, but the format
        result = self.sync_model.is_psw_format_good(psw)
        self.assertEqual(result, True)

    # def getSheetIndex(self, sync_data, lineIndex):
    def test_getSheetIndex(self):
        # Assert that it return the right is value
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 1)
        self.assertEqual(10, result)

        # Assert that it return -1 is the value is a float
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 5)
        self.assertEqual(-1, result)

        # Assert that it return -1 is the value is a string
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 6)
        self.assertEqual(-1, result)

        # Assert that it return -1 is the value is an empty string
        result, msg = self.sync_model.getSheetIndex(self.sync_data, 7)
        self.assertEqual(-1, result)

        # Same asserts, but check that we can change the order of the tab and it will still work
        result, msg = self.sync_model.getSheetIndex(
            self.sync_data_order_changed, 1)
        self.assertEqual(10, result)
        result, msg = self.sync_model.getSheetIndex(
            self.sync_data_order_changed, 5)
        self.assertEqual(-1, result)
        result, msg = self.sync_model.getSheetIndex(
            self.sync_data_order_changed, 6)
        self.assertEqual(-1, result)
        result, msg = self.sync_model.getSheetIndex(
            self.sync_data_order_changed, 7)
        self.assertEqual(-1, result)
