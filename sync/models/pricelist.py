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


class sync_pricelist():

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

# follows same pattern
    def syncPricelist(self):
        sheetWidth = 31
        i = 1

        columns = dict()
        columnsMissing = False
        msg = ""
        if ("SKU" in self.sheet[0]):
            columns["sku"] = self.sheet[0].index("SKU")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "SKU Missing")
            columnsMissing = True

        if ("EN-Name" in self.sheet[0]):
            columns["eName"] = self.sheet[0].index("EN-Name")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "EN-Name Missing")
            columnsMissing = True

        if ("EN-Description" in self.sheet[0]):
            columns["eDisc"] = self.sheet[0].index("EN-Description")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header",
                                     "EN-Description Missing")
            columnsMissing = True

        if ("FR-Name" in self.sheet[0]):
            columns["fName"] = self.sheet[0].index("FR-Name")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "FR-Name Missing")
            columnsMissing = True

        if ("FR-Description" in self.sheet[0]):
            columns["fDisc"] = self.sheet[0].index("FR-Description")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header",
                                     "FR-Description Missing")
            columnsMissing = True

        if ("isSoftware" in self.sheet[0]):
            columns["isSoftware"] = self.sheet[0].index("isSoftware")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "isSoftwareMissing")
            columnsMissing = True

        if ("Price CAD" in self.sheet[0]):
            columns["canPrice"] = self.sheet[0].index("Price CAD")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Price CAD Missing")
            columnsMissing = True

        if ("Price USD" in self.sheet[0]):
            columns["usPrice"] = self.sheet[0].index("Price USD")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Price USD Missing")
            columnsMissing = True

        if ("Can Rental" in self.sheet[0]):
            columns["canRental"] = self.sheet[0].index("Can Rental")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Can Rental Missing")
            _logger.info(msg)
            columnsMissing = True

        if ("US Rental" in self.sheet[0]):
            columns["usRental"] = self.sheet[0].index("US Rental")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "US Rental Missing")
            columnsMissing = True

        if ("Publish_CA" in self.sheet[0]):
            columns["canPublish"] = self.sheet[0].index("Publish_CA")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Publish_CA Missing")
            columnsMissing = True

        if ("Publish_USA" in self.sheet[0]):
            columns["usPublish"] = self.sheet[0].index("Publish_USA")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Publish_USA Missing")
            columnsMissing = True

        if ("Can_Be_Sold" in self.sheet[0]):
            columns["canBeSold"] = self.sheet[0].index("Can_Be_Sold")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Can_Be_Sold Missing")
            columnsMissing = True

        if ("E-Commerce_Website_Code" in self.sheet[0]):
            columns["ecommerceWebsiteCode"] = self.sheet[0].index(
                "E-Commerce_Website_Code")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header",
                                     "E-Commerce_Website_Code Missing")
            columnsMissing = True
        if ("CAN PL SEL" in self.sheet[0]):
            columns["canPricelist"] = self.sheet[0].index("CAN PL SEL")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "CAN PL SEL Missing")
            columnsMissing = True

        if ("CAN PL ID" in self.sheet[0]):
            columns["canPLID"] = self.sheet[0].index("CAN PL ID")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "CAN PL ID Missing")
            columnsMissing = True

        if ("USD PL SEL" in self.sheet[0]):
            columns["usPricelist"] = self.sheet[0].index("USD PL SEL")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "USD PL SEL Missing")
            columnsMissing = True

        if ("US PL ID" in self.sheet[0]):
            columns["usPLID"] = self.sheet[0].index("US PL ID")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "USD PL ID Missing")
            columnsMissing = True

        if ("CAN R SEL" in self.sheet[0]):
            columns["canrPricelist"] = self.sheet[0].index("CAN R SEL")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "USD PL SEL Missing")
            columnsMissing = True

        if ("CAN R ID" in self.sheet[0]):
            columns["canRID"] = self.sheet[0].index("CAN R ID")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "CAN R ID Missing")
            columnsMissing = True

        if ("US R SEL" in self.sheet[0]):
            columns["usrPricelist"] = self.sheet[0].index("US R SEL")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "US R SEL Missing")
            columnsMissing = True

        if ("US R ID" in self.sheet[0]):
            columns["usRID"] = self.sheet[0].index("US R ID")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "USD R ID Missing")
            columnsMissing = True

        if ("ECOM-FOLDER" in self.sheet[0]):
            columns["folder"] = self.sheet[0].index("ECOM-FOLDER")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "ECOM-FOLDER Missing")
            columnsMissing = True

        if ("ECOM-MEDIA" in self.sheet[0]):
            columns["media"] = self.sheet[0].index("ECOM-MEDIA")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "ECOM-MEDIA Missing")
            columnsMissing = True

        if ("Continue" in self.sheet[0]):
            columns["continue"] = self.sheet[0].index("Continue")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Continue Missing")
            columnsMissing = True

        if ("Valid" in self.sheet[0]):
            columns["valid"] = self.sheet[0].index("Valid")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Valid Missing")
            columnsMissing = True

        if (len(self.sheet[i]) != sheetWidth or columnsMissing):
            msg = "<h1>Pricelist page Invalid</h1>\n<p>" + str(self.name) + " width is: " + str(len(self.sheet[i])) + " Expected " + \
                str(sheetWidth) + "</p>\n" + msg
            self.database.sendSyncReport(msg)
            _logger.info(msg)
            return True, msg
        # msg = self.startTable(msg, sheetWidth)
        while (True):
            if (i == len(self.sheet) or str(self.sheet[i][columns["continue"]]) != "TRUE"):
                break
            if (str(self.sheet[i][columns["valid"]]) != "TRUE"):
                i = i + 1
                continue

            key = self.sheet[i][columns["sku"]]
            if (not utilities.check_id(str(key))):
                msg = utilities.buildMSG(
                    msg, self.name, key, "Key Error")
                i = i + 1
                continue

            if (not utilities.check_id(str(self.sheet[i][columns["canPLID"]]))):
                msg = utilities.buildMSG(
                    msg, self.name, key, "Canada Pricelist ID Invalid")
                i = i + 1
                continue

            if (not utilities.check_id(str(self.sheet[i][columns["usPLID"]]))):
                msg = utilities.buildMSG(
                    msg, self.name, key, "US Pricelist ID Invalid")
                i = i + 1
                continue

            if (not utilities.check_price(self.sheet[i][columns["canPrice"]])):
                msg = utilities.buildMSG(
                    msg, self.name, key, "Canada Price Invalid")
                i = i + 1
                continue

            if (not utilities.check_price(self.sheet[i][columns["usPrice"]])):
                msg = utilities.buildMSG(
                    msg, self.name, key, "US Price Invalid")
                i = i + 1
                continue

            try:
                product, new = self.pricelistProduct(
                    sheetWidth, i, columns)
                if (product.stringRep == str(self.sheet[i][:]) and SKIP_NO_CHANGE):
                    i = i + 1
                    continue

                self.pricelist(product, "canPrice",
                               "CAN Pricelist", i, columns)
                self.pricelist(product, "canRental",
                               "CAN RENTAL", i, columns)
                self.pricelist(product, "usPrice", "USD Pricelist", i, columns)
                self.pricelist(product, "usRental", "USD RENTAL", i, columns)

                if (new):
                    _logger.info("Blank StringRep")
                    product.stringRep = ""
                else:
                    _logger.info("Pricelist Price StringRep")
                    product.stringRep = str(self.sheet[i][:])
            except Exception as e:
                _logger.info(e)
                return True, msg

            i = i + 1
        return False, msg

    def pricelistProduct(self, sheetWidth, i, columns):
        external_id = str(self.sheet[i][columns["sku"]])
        product_ids = self.database.env['ir.model.data'].search(
            [('name', '=', external_id), ('model', '=', 'product.template')])
        if (len(product_ids) > 0):
            return self.updatePricelistProducts(self.database.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheetWidth, i, columns), False
        else:
            return self.createPricelistProducts(external_id, sheetWidth, i, columns), True

    def pricelist(self, product, priceName, pricelistName, i, columns):
        price = self.sheet[i][columns[priceName]]
        product_sync_common.addProductToPricelist(
            self.database, product, pricelistName, price)

    def updatePricelistProducts(self, product, sheetWidth, i, columns):

        if (product.stringRep == str(self.sheet[i][:]) and product.stringRep != "" and SKIP_NO_CHANGE):
            return product

        product.name = self.sheet[i][columns["eName"]]
        product.description_sale = self.sheet[i][columns["eDisc"]]

        product.ecom_folder = self.sheet[i][columns["folder"]]
        product.ecom_media = self.sheet[i][columns["media"]].upper()

        if (str(self.sheet[i][columns["isSoftware"]]) == "TRUE"):
            product.is_software = True
        else:
            product.is_software = False

        if (str(self.sheet[i][columns["canPrice"]]) != " " and str(self.sheet[i][columns["canPrice"]]) != ""):
            product.price = self.sheet[i][columns["canPrice"]]
            product.cadVal = self.sheet[i][columns["canPrice"]]

        if (str(self.sheet[i][columns["usPrice"]]) != " " and str(self.sheet[i][columns["usPrice"]]) != ""):
            product.usdVal = self.sheet[i][columns["usPrice"]]

        if (str(self.sheet[i][columns["canPublish"]]) == "TRUE"):
            product.is_published = True
        else:
            product.is_published = False
        if (str(self.sheet[i][columns["canPublish"]]) == "TRUE"):
            product.is_ca = True
        else:
            product.is_ca = False
        if (str(self.sheet[i][columns["usPublish"]]) == "TRUE"):
            product.is_us = True
        else:
            product.is_us = False

        if (str(self.sheet[i][columns["canBeSold"]]) == "TRUE"):
            product.sale_ok = True
        else:
            product.sale_ok = False

        product.storeCode = self.sheet[i][columns["ecommerceWebsiteCode"]]
        product.tracking = "serial"
        product.type = "product"

        _logger.info("Translate")
        product_sync_common.translatePricelist(
            self.database, product, self.sheet[i][columns["fName"]], self.sheet[i][columns["fDisc"]], "fr_CA")
        product_sync_common.translatePricelist(
            self.database, product, self.sheet[i][columns["eName"]], self.sheet[i][columns["eDisc"]], "en_US")

        return product

    def createPricelistProducts(self, external_id, sheetWidth, i, columns):
        ext = self.database.env['ir.model.data'].create(
            {'name': external_id, 'model': "product.template"})[0]
        product = self.database.env['product.template'].create(
            {'name': self.sheet[i][columns["eName"]]})[0]
        ext.res_id = product.id
        self.updatePricelistProducts(
            product, sheetWidth, i, columns)
        return product
