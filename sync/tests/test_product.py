
from odoo.tests import TransactionCase
import logging

from odoo.addons.sync.models.product import sync_products
_logger = logging.getLogger(__name__)

# To run the test, open the console and type :
# odoo-bin --test-enable -i sync


class product_test(TransactionCase):
    def setUp(self):
        super(product_test, self).setUp()
        _logger.error("Test Product Sync")
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

        self.sync_model = self.env['sync.sync']
        self.sync_product = sync_products(
            "Test Sheet", self.sheet_index_30, self.sync_model)
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
        product = self.sync_product.createProducts(external_id, product_name)

        # Assert that if a product is created, it their is only on SKU with this value
        product_exsiting = self.env['product.template'].search(
            [('sku', '=', product.sku)])
        self.assertEqual((len(product_exsiting) == 1), True)

    # Test to be done after a product update

    def aftertest_updateProducts(
            self,
            product_id,
            external_id,
            product_name_english,
            product_name_french,
            product_stringRep,
            product_description_sale_english,
            product_description_sale_french,
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
        self.assertEqual((product_updated.name == product_name_english), True)
        self.assertEqual(
            (product_updated.stringRep == product_stringRep), True)
        self.assertEqual(product_updated.description_sale,
                         product_description_sale_english)
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

        self.aftertest_product_translations(
            product_id, product_name_english, product_description_sale_english, 'en_US')
        self.aftertest_product_translations(
            product_id, product_name_french, product_description_sale_french, 'fr_CA')

    def aftertest_product_translations(self, product_id, name, description, lang):
        pass

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
        product_name_english = "Name of the product(English)"
        product_name_french = "Name of the product(French)"
        product_description_sale_english = "Description of the product(English)"
        product_description_sale_french = "Description of the product(French)"
        product_price_cad = "3850"
        product_price_usd = "2980"
        product_tracking = "serial"
        product_type = "product"

        product = self.sync_product.createProducts(
            external_id, product_name_english)
        product_not_updated = self.env['product.template'].search(
            [('id', '=', product.id)])

        # Assert that the product created match the tests values.
        self.assertEqual((product_not_updated.sku == external_id), True)
        self.assertEqual((product_not_updated.name ==
                         product_name_english), True)
        self.assertEqual(
            (product_not_updated.tracking == product_tracking), True)
        self.assertEqual((product_not_updated.type == product_type), True)

        # Validate that the test value are not set before the method is executed.
        self.assertEqual(
            (product_not_updated.stringRep == product_stringRep), False)
        self.assertEqual((product_not_updated.description_sale ==
                         product_description_sale_english), False)
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
        self.sync_product.updateProducts(
            product,
            product_stringRep,
            product_name_english,
            product_name_french,
            product_description_sale_english,
            product_description_sale_french,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type)

        self.aftertest_updateProducts(
            product.id,
            external_id,
            product_name_english,
            product_name_french,
            product_stringRep,
            product_description_sale_english,
            product_description_sale_french,
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
        product_name_english = "Name of the product(English)"
        product_name_french = "Name of the product(French)"
        product_description_sale_english = "Description of the product(English)"
        product_description_sale_french = "Description of the product(French)"
        product_price_cad = "3850"
        product_price_usd = "2980"
        product_tracking = "serial"
        product_type = "product"

        self.pretest_createProducts(external_id)

        # Callind the method
        product = self.sync_product.createAndUpdateProducts(
            external_id,
            product_stringRep,
            product_name_english,
            product_name_french,
            product_description_sale_english,
            product_description_sale_french,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type)

        self.aftertest_updateProducts(
            product.id,
            external_id,
            product_name_english,
            product_name_french,
            product_stringRep,
            product_description_sale_english,
            product_description_sale_french,
            product_price_cad,
            product_tracking,
            product_type)

    # def archive_product(self, product_id):

    def test_archive_product(self):
        external_id = "SKU-1234123"
        product_name = "New product"
        product = self.sync_product.createProducts(external_id, product_name)

        # Validate that the product to archived is active before calling the method
        self.assertEqual(product.active, True)

        # calling the method
        self.sync_model.archive_product(str(product.id))

        product_modified = self.env['product.template'].search(
            [('id', '=', product.id)])
        # Assert that once archived, it is not active.
        self.assertEqual(product_modified.active, False)
