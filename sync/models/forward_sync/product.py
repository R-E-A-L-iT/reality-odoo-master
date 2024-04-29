# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

from .product_common import product_sync_common

_logger = logging.getLogger(__name__)

SKIP_NO_CHANGE = False


class sync_products:
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def syncProducts(self, sheet):
        # Confirm GS Tab is in the correct Format
       
        columns = dict()
        columnsMissing = False
        msg = ""
        i = 1

        # Check if the header match the appropriate format
        productHeaderDict = dict()
        productHeaderDict["SKU"]              = "sku"
        productHeaderDict["EN-Name"]          = "english_name"
        productHeaderDict["FR-Name"]          = "french_name"
        productHeaderDict["EN-Description"]   = "english_description"
        productHeaderDict["FR-Description"]   = "french_description"
        productHeaderDict["PriceCAD"]        = "priceCAD"
        productHeaderDict["PriceUSD"]        = "priceUSD"
        productHeaderDict["Product Type"]     = "type"
        productHeaderDict["Tracking"]         = "tracking"
        productHeaderDict["CanBeSold"]        = "can_be_sold"
        productHeaderDict["Valid"]            = "valid"
        productHeaderDict["Continue"]         = "continue"    
        sheetWidth = len(productHeaderDict)                                            
        columns, msg, columnsMissing = utilities.checkSheetHeader(productHeaderDict, self.sheet, self.name)

        if sheetWidth != len(sheet[i]) or columnsMissing:
            msg = (
                "<h1>Product page Invalid</h1>\n<p>"
                + str(self.name)
                + " width is: "
                + str(len(self.sheet[i]))
                + " Expected "
                + str(sheetWidth)
                + "</p>\n"
                + msg
            )
            self.database.sendSyncReport(msg)
            _logger.info(msg)
            return True, msg

        # loop through all the rows        
        while True:
            # check if should continue
            if str(sheet[i][columns["continue"]]).upper() != "TRUE":
                break

            # validation checks
            # Primary Key used in Google Sheet Database
            key = str(sheet[i][columns["sku"]])
            if not utilities.check_id(key):
                msg = utilities.buildMSG(msg, self.name, key, "Key Error")
                i += 1
                continue

            if not utilities.check_price(sheet[i][columns["priceCAD"]]):
                msg = utilities.buildMSG(msg, self.name, key, "CAD Price Invalid")
                i += 1
                continue

            if not utilities.check_price(sheet[i][columns["priceUSD"]]):
                msg = utilities.buildMSG(msg, self.name, key, "USD Price Invalid")
                i += 1
                continue

            # if it gets here data should be valid
            try:
                # attempts to access existing item (item/row)
                external_id = str(sheet[i][columns["sku"]])
                product_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", external_id), ("model", "=", "product.template")]
                )
                
                if (str(external_id) == "CCP-00108-49440-00034-16345-DEF7C"):
                    _logger.info('external_id: ' + str(external_id) + ', len(product_ids): ' + str(len(product_ids)))

                if len(product_ids) > 0:
                    product = self.database.env["product.template"].browse(
                        product_ids[len(product_ids) - 1].res_id
                    )

                    if (str(external_id) == "CCP-00108-49440-00034-16345-DEF7C"):
                        _logger.info('len(product): ' + str(len(product)))
                    
                    if len(product) != 1:
                        msg = utilities.buildMSG(
                            msg,
                            self.name,
                            key,
                            "Product ID Recognized But Product Count is Invalid",
                        )
                        i = i + 1
                        continue

                    if (str(external_id) == "CCP-00108-49440-00034-16345-DEF7C"):
                        _logger.info('product,sku: ' + str(product.sku))

                    self.updateProducts(
                        product,
                        str(sheet[i][:]),  # product_stringRep
                        sheet[i][columns["english_name"]],
                        sheet[i][columns["french_name"]],
                        sheet[i][columns["english_description"]],
                        sheet[i][columns["french_description"]],
                        sheet[i][columns["priceCAD"]],  # product_price_cad
                        sheet[i][columns["priceUSD"]],  # product_price_usd
                        "serial",  # product_tracking
                        "product",
                        sheet[i][columns["can_be_sold"]]
                    )  # product_type
                else:
                    self.createAndUpdateProducts(
                        external_id,
                        str(sheet[i][:]),  # product_stringRep
                        sheet[i][columns["english_name"]],
                        sheet[i][columns["french_name"]],
                        sheet[i][columns["english_description"]],
                        sheet[i][columns["french_description"]],
                        sheet[i][columns["priceCAD"]],  # product_price_cad
                        sheet[i][columns["priceUSD"]],  # product_price_usd
                        "serial",  # product_tracking
                        "product",
                        sheet[i][columns["can_be_sold"]]
                    )  # product_type

            except Exception as e:
                _logger.info("Products Exception")
                _logger.error(e)
                msg = utilities.buildMSG(msg, self.name, key, str(e))
                return True, msg

            i += 1

        return False, msg

    # Method to create a product
    # Input
    #   external_id:    The external id, wich is the SKU key in the GoogleSheet Database.
    #   product_name:   Name of the product
    # Output
    #   product:        The product generated by Odoo

    def createProducts(self, external_id, product_name):
        # creates record
        product = None
        ext = self.database.env["ir.model.data"].create(
            {"name": external_id, "model": "product.template"}
        )[0]
        product = self.database.env["product.template"].create({"name": product_name})[
            0
        ]

        product.tracking = "serial"
        product.type = "product"
        ext.res_id = product.id

        _logger.info("Created Product" + str(product.name))

        return product

    # Methode to update product information.
    # Input
    #   product:                    The product generated with product.template model
    #   product_stringRep:          The GoogleSheet line that represent all the informations of the product
    #   product_name:               Product Name
    #   product_description_sale:   English dercription
    #   product_price_cad:          Price in CAD
    #   product_price_usd:          Price in USD
    #   product_tracking:           Tracking
    #   product_type:               Type
    #   product.sale_ok             can_be_sold if the product can be sold or not

    def updateProducts(
        self,
        product,
        product_stringRep,
        product_name_english,
        product_name_french,
        product_description_sale_english,
        product_description_sale_french,
        product_price_cad,
        product_price_usd,
        product_tracking,
        product_type,
        can_be_sold
    ):
        # check if any update to item is needed and skips if there is none
        if product.stringRep == product_stringRep and SKIP_NO_CHANGE:
            return

        # reads values and puts them in appropriate fields
        product.name = product_name_english

        product_sync_common.translatePricelist(
            self.database,
            product,
            product_name_english,
            product_description_sale_english,
            "en_US",
        )
        product_sync_common.translatePricelist(
            self.database,
            product,
            product_name_french,
            product_description_sale_french,
            "fr_CA",
        )

        product.description_sale = product_description_sale_english
        _logger.warning("Tracking")
        # product.tracking = product_tracking
        product.type = product_type
        product.stringRep = product_stringRep
        # pricelist need to be done before modifiyng the product.price
        # since it will be erased be the addProductToPricelist.  Apparently,
        # Odoo set to price to 0 if we set the product in a pricelist.
        product_sync_common.addProductToPricelist(
            self.database, product, "CAD SALE", product_price_cad
        )
        product_sync_common.addProductToPricelist(
            self.database, product, "USD SALE", product_price_usd
        )
        product.price = product_price_cad

        product.sale_ok = can_be_sold

        _logger.info('product.sku: ' + str(product.sku))                               
        if (str(product.sku) == "CCP-00108-49440-00034-16345-DEF7C"):
            _logger.info('CCP-00108-49440-00034-16345-DEF7C')
            _logger.info('product.sale_ok: ' + str(product.sale_ok))


    # Method to create and update a product
    # Input
    #   external_id:                The SKU in GoogleSheet
    #   product_stringRep:          The GoogleSheet line that represent all the informations of the product
    #   product_name:               Product Name
    #   product_description_sale:   English dercription
    #   product_price_cad:          Price in CAD
    #   product_price_usd:          Price in USD
    #   product_tracking:           Tracking
    #   product_type:               Type
    #   product.sale_ok             can_be_sold if the product can be sold or not    
    # Output
    #   product:                    The product created

    def createAndUpdateProducts(
        self,
        external_id,
        product_stringRep,
        product_name_english,
        product_name_french,
        product_description_sale_english,
        product_description_sale_french,
        product_price_cad,
        product_price_usd,
        product_tracking,
        product_type,
        can_be_sold
    ):
        # creates record and updates it
        product = self.createProducts(external_id, product_name_english)
        self.updateProducts(
            product,
            product_stringRep,
            product_name_english,
            product_name_french,
            product_description_sale_english,
            product_description_sale_french,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type,
            can_be_sold
        )

        product_created = self.database.env["product.template"].search(
            [("sku", "=", external_id)]
        )
        return product_created
