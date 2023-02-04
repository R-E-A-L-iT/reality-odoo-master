from odoo.tests import TransactionCase

# To run the test, open the console and type :
# odoo-bin --test-enable -i sync


class TestModuleProduct(transactioncase):

    def setUp(self):
        super(TestModuleProduct, self).setUp()
        self.pricelist_data = []
        self.sync_model = self.env['sync.sync']
        self.sync_product = self.sync_model.getSync_product(
            "TEST_DATA_ODOO", self.pricelist_data)

    # Test to be executer befor creating a product
    # Input
    #   external_id: Sku to check if not existing

    def pretest_createProducts(self, external_id):
        # Assert that the product to be created does not exist to validate the test.
        product_unexsiting = self.env['product.template'].search(
            [('sku', '=', external_id)])
        self.assertEqual((len(product_unexsiting) == 0), True)

    # def createProducts(self, external_id, product_name):

    def test_createProducts(self):
        external_id = "SKU-1234123"
        product_name = "New product"

        self.pretest_createProducts(external_id)

        # Calling the methode to test
        product = self.product_model.createProducts(external_id, product_name)

        # Assert that if a product is created, it their is only on SKU with this value
        product_exsiting = self.env['product.template'].search(
            [('sku', '=', product.sku)])
        self.assertEqual((len(product_exsiting) == 1), True)

    # Test to be done after a product update

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

        # Assert that if a product is created, the SKU is unique
        product_updated = self.env['product.template'].search(
            [('sku', '=', external_id)])
        self.assertEqual((len(product_updated) == 1), True)

        # Assert that if a product is created, the ID is unique
        product_updated = self.env['product.template'].search(
            [('id', '=', product_id)])
        self.assertEqual((len(product_updated) == 1), True)

        # Assert that all the test data is properly set in the updated product
        self.assertEqual((product_updated.sku == external_id), True)
        self.assertEqual((product_updated.name == product_name), True)
        self.assertEqual(
            (product_updated.stringRep == product_stringRep), True)
        self.assertEqual((product_updated.description_sale ==
                         product_description_sale), True)
        self.assertEqual((str(float(product_updated.price)) ==
                         str(float(product_price_cad))), True)
        self.assertEqual((product_updated.tracking == product_tracking), True)
        self.assertEqual((product_updated.type == product_type), True)

        # Assert that there is only one price per product in 'CAN pricelist' and 'USD pricelist'
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

    # def updateProducts(
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
        external_id = "SKU-123456"
        product_stringRep = "['SKU-123456', 'Name of the product', 'Description of the product', '3850', '2980', 'Product Type of the product', 'Tracking of the product', 'TRUE', 'TRUE']"
        product_name = "Name of the product"
        product_description_sale = "Description of the product"
        product_price_cad = "3850"
        product_price_usd = "2980"
        product_tracking = "serial"
        product_type = "product"

        product = self.sync_model.createProducts(external_id, product_name)
        product_not_updated = self.env['product.template'].search(
            [('id', '=', product.id)])

        # Assert that the product created match the tests values.
        self.assertEqual((product_not_updated.sku == external_id), True)
        self.assertEqual((product_not_updated.name == product_name), True)
        self.assertEqual(
            (product_not_updated.tracking == product_tracking), True)
        self.assertEqual((product_not_updated.type == product_type), True)

        # Validate that the test value are not set before the method is executed.
        self.assertEqual(
            (product_not_updated.stringRep == product_stringRep), False)
        self.assertEqual((product_not_updated.description_sale ==
                         product_description_sale), False)
        self.assertEqual(
            (product_not_updated.price == product_price_cad), False)

        # Assert that the 'CAN pricelist' and 'USD priclist' doest not contain information on the product.
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

        # calling the method to test
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
            product.id,
            external_id,
            product_name,
            product_stringRep,
            product_description_sale,
            product_price_cad,
            product_tracking,
            product_type)

    # def createAndUpdateProducts(
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
        external_id = "SKU-123456"
        product_stringRep = "['SKU-123456', 'Name of the product', 'Description of the product', '3850', '2980', 'Product Type of the product', 'Tracking of the product', 'TRUE', 'TRUE']"
        product_name = "Name of the product"
        product_description_sale = "Description of the product"
        product_price_cad = "3850"
        product_price_usd = "2980"
        product_tracking = "serial"
        product_type = "product"

        self.pretest_createProducts(external_id)

        # Callind the method
        product = self.product_model.createAndUpdateProducts(
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

    # def archive_product(self, product_id):

    def test_archive_product(self):
        external_id = "SKU-1234123"
        product_name = "New product"
        product = self.sync_model.createProducts(external_id, product_name)

        # Validate that the product to archived is active before calling the method
        self.assertEqual(product.active, True)

        # calling the method
        self.sync_model.archive_product(str(product.id))

        product_modified = self.env['product.template'].search(
            [('id', '=', product.id)])
        # Assert that once archived, it is not active.
        self.assertEqual(product_modified.active, False)

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
