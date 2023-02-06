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

    # def getColumnIndex (self, sheet, columnName):
    def test_getColumnIndex(self):
        # Assert that the method return the good data
        result = self.sync_model.getColumnIndex(self.sync_data, "Sheet Index")
        self.assertEqual((result == 1), True)

        # Assert that the method return -1 when column does not exist
        result = self.sync_model.getColumnIndex(
            self.sync_data, "Does not exists")
        self.assertEqual((result == -1), True)

    # def checkIfKeyExistInTwoDict(self, dict_small, dict_big):

    def test_checkIfKeyExistInTwoDict(self):
        a = dict()
        b = dict()
        c = dict()

        a[1] = "11"
        a[2] = "22"
        a[3] = "33"

        b[4] = "44"
        b[5] = "55"
        b[6] = "66"
        b[7] = "77"

        c[4] = "44"
        c[5] = "55"
        c[6] = "66"
        c[3] = "33"

        result_bool, result_str = self.sync_model.checkIfKeyExistInTwoDict(
            a, b)
        self.assertEqual(result_bool, False)
        self.assertEqual(result_str == "", True)

        result_bool, result_str = self.sync_model.checkIfKeyExistInTwoDict(
            a, c)
        self.assertEqual(result_bool, True)
        self.assertEqual(result_str == "3", True)

    # def checkOdooSyncDataTab(self, odoo_sync_data_sheet):

    def test_checkOdooSyncDataTab(self):

        self.sync_bad_data = [
            ['C1',              'B4',           'A',            'S',     'Z'],
            ['Companies_',	    '10',           'Companies',    'TRUE', 'TRUE'],
            ['Contacts_',       '20',           'Contacts',     'TRUE', 'TRUE'],
            ['Pricelist-1_',    '30',           'Pricelist',    'TRUE', 'TRUE'],
            ['CCP_-1_',         '40',           'CCP',          'TRUE', 'TRUE'],
            ['Products_',       '50.1',         'Products',     'TRUE', 'TRUE'],
            ['CCP_-2_',         'sdf',          'CCP',          'TRUE', 'TRUE'],
            ['',                '',             '',             'FALSE', 'FALSE'],
            ['',                'Loading...',   '',             'FALSE', 'FALSE']
        ]

        self.sync_data_missing_sheet_name = [
            ['Sheet Index',  'Model Type',   'Valid', 'Continue'],
            ['10',           'Companies',    'TRUE', 'TRUE'],
            ['20',           'Contacts',     'TRUE', 'TRUE'],
            ['30',           'Pricelist',    'TRUE', 'TRUE'],
            ['40',           'CCP',          'TRUE', 'TRUE'],
            ['50.1',         'Products',     'TRUE', 'TRUE'],
            ['sdf',          'CCP',          'TRUE', 'TRUE'],
            ['',             '',             'FALSE', 'FALSE'],
            ['Loading...',   '',             'FALSE', 'FALSE']
        ]

        self.sync_data_missing_sheet_index = [
            ['Sheet Name',   'Model Type',   'Valid', 'Continue'],
            ['Companies_',	 'Companies',    'TRUE', 'TRUE'],
            ['Contacts_',    'Contacts',     'TRUE', 'TRUE'],
            ['Pricelist-1_', 'Pricelist',    'TRUE', 'TRUE'],
            ['CCP_-1_',      'CCP',          'TRUE', 'TRUE'],
            ['Products_',    'Products',     'TRUE', 'TRUE'],
            ['CCP_-2_',      'CCP',          'TRUE', 'TRUE'],
            ['',             '',             'FALSE', 'FALSE'],
            ['',             '',             'FALSE', 'FALSE']
        ]

        self.sync_data_missing_model_type = [
            ['Sheet Name',      'Sheet Index',  'Valid', 'Continue'],
            ['Companies_',	    '10',           'TRUE', 'TRUE'],
            ['Contacts_',       '20',           'TRUE', 'TRUE'],
            ['Pricelist-1_',    '30',           'TRUE', 'TRUE'],
            ['CCP_-1_',         '40',           'TRUE', 'TRUE'],
            ['Products_',       '50.1',         'TRUE', 'TRUE'],
            ['CCP_-2_',         'sdf',          'TRUE', 'TRUE'],
            ['',                '',             'FALSE', 'FALSE'],
            ['',                'Loading...',   'FALSE', 'FALSE']
        ]

        self.sync_data_missing_valid = [
            ['Sheet Name',      'Sheet Index',  'Model Type',   'Continue'],
            ['Companies_',	    '10',           'Companies',    'TRUE'],
            ['Contacts_',       '20',           'Contacts',     'TRUE'],
            ['Pricelist-1_',    '30',           'Pricelist',    'TRUE'],
            ['CCP_-1_',         '40',           'CCP',          'TRUE'],
            ['Products_',       '50.1',         'Products',     'TRUE'],
            ['CCP_-2_',         'sdf',          'CCP',          'TRUE'],
            ['',                '',             '',             'FALSE'],
            ['',                'Loading...',   '',             'FALSE']
        ]

        self.sync_data_missing_continue = [
            ['Sheet Name',      'Sheet Index',  'Model Type',   'Valid'],
            ['Companies_',	    '10',           'Companies',    'TRUE'],
            ['Contacts_',       '20',           'Contacts',     'TRUE'],
            ['Pricelist-1_',    '30',           'Pricelist',    'TRUE'],
            ['CCP_-1_',         '40',           'CCP',          'TRUE'],
            ['Products_',       '50.1',         'Products',     'TRUE'],
            ['CCP_-2_',         'sdf',          'CCP',          'TRUE'],
            ['',                '',             '',             'FALSE'],
            ['',                'Loading...',   '',             'FALSE']
        ]

        # Assert that it return the right information
        result = self.sync_model.checkOdooSyncDataTab(self.sync_data)
        self.assertEqual(
            result['odoo_sync_data_sheet_name_column_index'] == 0, True)
        self.assertEqual(
            result['odoo_sync_data_sheet_index_column_index'] == 1, True)
        self.assertEqual(
            result['odoo_sync_data_model_type_column_index'] == 2, True)
        self.assertEqual(
            result['odoo_sync_data_valid_column_index'] == 3, True)
        self.assertEqual(
            result['odoo_sync_data_continue_column_index'] == 4, True)

        # Assert it raise the exception when one column is missing.
        with self.assertRaises(Exception):
            result = self.sync_model.checkOdooSyncDataTab(
                self.sync_data_missing_sheet_name)

        with self.assertRaises(Exception):
            result = self.sync_model.checkOdooSyncDataTab(
                self.sync_data_missing_sheet_index)

        with self.assertRaises(Exception):
            result = self.sync_model.checkOdooSyncDataTab(
                self.sync_data_missing_model_type)

        with self.assertRaises(Exception):
            result = self.sync_model.checkOdooSyncDataTab(
                self.sync_data_missing_valid)

        with self.assertRaises(Exception):
            result = self.sync_model.checkOdooSyncDataTab(
                self.sync_data_missing_continue)

    # def getAllValueFromColumn(self, sheet, column_name):

    def test_getAllValueFromColumn(self):
        sheet = [
            ['SKU', 	 'EN-Name', 'Valid', 'Continue'],
            ['SKU-1111', 'EN-Name-1111', 'TRUE', 'TRUE'],
            ['SKU-1112', 'EN-Name-1112', 'TRUE', 'TRUE'],
            ['SKU-1113', 'EN-Name-1113', 'FALSE', 'TRUE'],
            ['SKU-1114', 'EN-Name-1114', 'TRUE', 'TRUE'],
            ['SKU-1115', 'EN-Name-1115', 'FALSE', 'FALSE']
        ]

        sheet_no_valid = [
            ['SKU', 	 'EN-Name', 'Continue'],
            ['SKU-1111', 'EN-Name-1111', 'TRUE'],
            ['SKU-1112', 'EN-Name-1112', 'TRUE'],
            ['SKU-1113', 'EN-Name-1113', 'TRUE'],
            ['SKU-1114', 'EN-Name-1114', 'FALSE'],
            ['SKU-1115', 'EN-Name-1115', 'FALSE']
        ]

        sheet_no_continue = [
            ['SKU', 	 'EN-Name', 'Valid'],
            ['SKU-1111', 'EN-Name-1111', 'TRUE'],
            ['SKU-1112', 'EN-Name-1112', 'TRUE'],
            ['SKU-1113', 'EN-Name-1113', 'TRUE'],
            ['SKU-1114', 'EN-Name-1114', 'FALSE'],
            ['SKU-1115', 'EN-Name-1115', 'FALSE']
        ]

        sku_dict = self.sync_model.getAllValueFromColumn(sheet, "SKU")

        self.assertEqual('SKU-1111' in sku_dict, True)
        self.assertEqual(sku_dict['SKU-1111'] == "SKU", True)

        self.assertEqual('SKU-1112' in sku_dict, True)
        self.assertEqual(sku_dict['SKU-1112'] == "SKU", True)

        self.assertEqual('SKU-1113' in sku_dict, False)

        self.assertEqual('SKU-1114' in sku_dict, True)
        self.assertEqual(sku_dict['SKU-1114'] == "SKU", True)

        self.assertEqual('SKU-1115' in sku_dict, False)

        with self.assertRaises(Exception):
            sku_dict = self.sync_model.getAllValueFromColumn(
                sheet, "NOT_EXISTING")

        with self.assertRaises(Exception):
            sku_dict = self.sync_model.getAllValueFromColumn(
                sheet_no_valid, "SKU")

        with self.assertRaises(Exception):
            sku_dict = self.sync_model.getAllValueFromColumn(
                sheet_no_continue, "SKU")
