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

SKIP_NO_CHANGE = True


class sync_products:
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def syncProducts(self, sheet):
        # Confirm GS Tab is in the correct Format
        sheetWidth = 11
        columns = dict()
        columnsMissing = False
        msg = ""
        i = 1

        productHeaderDict = dict()
        productHeaderDict["SKU"]              = "sku"
        productHeaderDict["EN-Name"]          = "english_name"
        productHeaderDict["FR-Name"]          = "french_name"
        productHeaderDict["EN-Description"]   = "english_description"
        productHeaderDict["FR-Description"]   = "french_description"
        productHeaderDict["Price CAD"]        = "priceCAD"
        productHeaderDict["Price USD"]        = "priceUSD"
        productHeaderDict["Product Type"]     = "type"
        productHeaderDict["Tracking"]         = "tracking"
        productHeaderDict["Valid"]            = "valid"
        productHeaderDict["Continue"]         = "continue"                                                

        # Calculate Indexes
        # if "SKU" in sheet[0]:
        #     columns["sku"] = sheet[0].index("SKU")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "SKU Missing")
        #     columnsMissing = "SKU"

        # if "EN-Name" in sheet[0]:
        #     columns["english_name"] = sheet[0].index("EN-Name")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "EN-Name Missing")
        #     columnsMissing = "EN-Name"

        # if "FR-Name" in sheet[0]:
        #     columns["french_name"] = sheet[0].index("FR-Name")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "FR-Name Missing")
        #     columnsMissing = "FR-Name"

        # if "EN-Description" in sheet[0]:
        #     columns["english_description"] = sheet[0].index("EN-Description")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Description Missing")
        #     columnsMissing = "Description"

        # if "FR-Description" in sheet[0]:
        #     columns["french_description"] = sheet[0].index("FR-Description")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Description Missing")
        #     columnsMissing = "Description"

        # if "Price CAD" in sheet[0]:
        #     columns["priceCAD"] = sheet[0].index("Price CAD")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Price CAD Missing")
        #     columnsMissing = "Price CAD"

        # if "Price USD" in sheet[0]:
        #     columns["priceUSD"] = sheet[0].index("Price USD")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Price USD")
        #     columnsMissing = "Price USD"

        # if "Product Type" in sheet[0]:
        #     columns["type"] = sheet[0].index("Product Type")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Product Type")
        #     columnsMissing = "Product Type"

        # if "Tracking" in sheet[0]:
        #     columns["tracking"] = sheet[0].index("Tracking")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Tracking Missing")
        #     columnsMissing = "Tracking"

        # if "Valid" in sheet[0]:
        #     columns["valid"] = sheet[0].index("Valid")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Valid Missing")
        #     columnsMissing = "Valid"

        # if "Continue" in sheet[0]:
        #     columns["continue"] = sheet[0].index("Continue")
        # else:
        #     msg = utilities.buildMSG(msg, self.name, "Header", "Header Missing")
        #     columnsMissing = "Continue"

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

                if len(product_ids) > 0:
                    product = self.database.env["product.template"].browse(
                        product_ids[len(product_ids) - 1].res_id
                    )
                    if len(product) != 1:
                        msg = utilities.buildMSG(
                            msg,
                            self.name,
                            key,
                            "Product ID Recognized But Product Count is Invalid",
                        )
                        i = i + 1
                        continue
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
    ):
        # check if any update to item is needed and skips if there is none
        if product.stringRep == product_stringRep:
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
        )

        product_created = self.database.env["product.template"].search(
            [("sku", "=", external_id)]
        )
        return product_created
