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


class sync_pricelist:
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database


    ##################################################
    def syncPricelist(self):
        # Confirm GS Tab is in the correct Format
        sheetWidth = 33
        i = 1

        columns = dict()
        columnsMissing = False
        msg = ""

        pricelistHeaderDict = dict()
        pricelistHeaderDict["SKU"]              = "sku"
        pricelistHeaderDict["EN-Name"]          = "eName"
        pricelistHeaderDict["EN-Description"]   = "eDisc"
        pricelistHeaderDict["FR-Name"]          = "fName"
        pricelistHeaderDict["FR-Description"]   = "fDisc"
        pricelistHeaderDict["isSoftware"]       = "isSoftware"
        pricelistHeaderDict["Type"]             = "type"
        pricelistHeaderDict["Price CAD"]        = "cadSale"
        pricelistHeaderDict["Price USD"]        = "usdSale"
        pricelistHeaderDict["Can Rental"]       = "cadRental"
        pricelistHeaderDict["US Rental"]        = "usdRental"
        pricelistHeaderDict["Publish_CA"]       = "canPublish"
        pricelistHeaderDict["Publish_USA"]      = "usPublish"
        pricelistHeaderDict["Can_Be_Sold"]      = "canBeSold"
        pricelistHeaderDict["Can_Be_Rented"]    = "canBeRented"
        pricelistHeaderDict["E-Commerce_Website_Code"] = "ecommerceWebsiteCode"
        pricelistHeaderDict["CAN PL ID"]        = "canPLID"
        pricelistHeaderDict["US PL ID"]         = "usPLID"
        pricelistHeaderDict["CAN R SEL"]        = "canrPricelist"
        pricelistHeaderDict["CAN R ID"]         = "canRID"
        pricelistHeaderDict["US R SEL"]         = "usrPricelist"
        pricelistHeaderDict["US R ID"]          = "usRID"
        pricelistHeaderDict["ECOM-FOLDER"]      = "folder"
        pricelistHeaderDict["ECOM-MEDIA"]       = "media"
        pricelistHeaderDict["Continue"]         = "continue"
        pricelistHeaderDict["Valid"]            = "valid"
       

        columns, msg, columnsMissing = utilities.checkSheetHeader(pricelistHeaderDict, self.sheet, self.name)  

        # for row in pricelistHeaderDict:
        #     if row in self.sheet[0]:
        #         columns[pricelistHeaderDict[row]] = self.sheet[0].index(row)
        #     else:
        #         msg = utilities.buildMSG(msg, self.name, "Header", str(row) + " Missing")
        #         columnsMissing = True

        if len(self.sheet[i]) != sheetWidth or columnsMissing:
            msg = (
                "<h1>Pricelist page Invalid</h1>\n<p>"
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
            if (
                i == len(self.sheet)
                or str(self.sheet[i][columns["continue"]]) != "TRUE"
            ):
                break

            # validation checks
            if str(self.sheet[i][columns["valid"]]) != "TRUE":
                i = i + 1
                continue

            key = self.sheet[i][columns["sku"]]
            if not utilities.check_id(str(key)):
                msg = utilities.buildMSG(msg, self.name, key, "Key Error")
                i = i + 1
                continue

            if not utilities.check_id(str(self.sheet[i][columns["canPLID"]])):
                msg = utilities.buildMSG(
                    msg, self.name, key, "Canada Pricelist ID Invalid"
                )
                i = i + 1
                continue

            if not utilities.check_id(str(self.sheet[i][columns["usPLID"]])):
                msg = utilities.buildMSG(msg, self.name, key, "US Pricelist ID Invalid")
                i = i + 1
                continue

            if not utilities.check_price(self.sheet[i][columns["cadSale"]]):
                msg = utilities.buildMSG(msg, self.name, key, "Canada Price Invalid")
                i = i + 1
                continue

            if not utilities.check_price(self.sheet[i][columns["usdSale"]]):
                msg = utilities.buildMSG(msg, self.name, key, "US Price Invalid")
                i = i + 1
                continue

            # if it gets here data should be valid
            try:
                # Creates or fetch corrisponding record
                product, new = self.pricelistProduct(sheetWidth, i, columns)
                if product.stringRep == str(self.sheet[i][:]) and SKIP_NO_CHANGE:
                    i = i + 1
                    continue
                # Add Prices to the 4 pricelists
                self.pricelist(product, "cadSale", "CAD SALE", i, columns)
                self.pricelist(product, "cadRental", "CAD RENTAL", i, columns)
                self.pricelist(product, "usdSale", "USD SALE", i, columns)
                self.pricelist(product, "usdRental", "USD RENTAL", i, columns)

                if new:
                    product.stringRep = ""
                else:
                    product.stringRep = str(self.sheet[i][:])
            except Exception as e:
                _logger.error(e)
                msg = utilities.buildMSG(msg, self.name, key, str(e))
                return True, msg                   

            i = i + 1           
        return False, msg

    def pricelistProduct(self, sheetWidth, i, columns):
        # attempts to access existing item (item/row)
        external_id = str(self.sheet[i][columns["sku"]])
        product_ids = self.database.env["ir.model.data"].search(
            [("name", "=", external_id), ("model", "=", "product.template")]
        )
        if len(product_ids) > 0:
            return (
                self.updatePricelistProducts(
                    self.database.env["product.template"].browse(
                        product_ids[len(product_ids) - 1].res_id
                    ),
                    i,
                    columns,
                ),
                False,
            )
        else:
            product = self.createPricelistProducts(
                external_id, self.sheet[i][columns["eName"]]
            )
            product = self.updatePricelistProducts(product, i, columns)
            return product, True

    def pricelist(self, product, priceName, pricelistName, i, columns):
        # Adds price to given pricelist
        price = self.sheet[i][columns[priceName]]
        product_sync_common.addProductToPricelist(
            self.database, product, pricelistName, price
        )

    def updatePricelistProducts(self, product, i, columns):
        # check if any update to item is needed and skips if there is none
        if (
            product.stringRep == str(self.sheet[i][:])
            and product.stringRep != ""
            and SKIP_NO_CHANGE
        ):
            return product

        # reads values and puts them in appropriate fields
        product.name = self.sheet[i][columns["eName"]]
        product.description_sale = self.sheet[i][columns["eDisc"]]

        product.ecom_folder = self.sheet[i][columns["folder"]]
        product.ecom_media = self.sheet[i][columns["media"]].upper()

        if str(self.sheet[i][columns["isSoftware"]]) == "TRUE":
            product.is_software = True
        else:
            product.is_software = False

        if (
            str(self.sheet[i][columns["cadSale"]]) != " "
            and str(self.sheet[i][columns["cadSale"]]) != ""
        ):
            product.price = self.sheet[i][columns["cadSale"]]
            product.cadVal = self.sheet[i][columns["cadSale"]]

        if (
            str(self.sheet[i][columns["usdSale"]]) != " "
            and str(self.sheet[i][columns["usdSale"]]) != ""
        ):
            product.usdVal = self.sheet[i][columns["usdSale"]]

        if str(self.sheet[i][columns["canPublish"]]) == "TRUE":
            product.is_published = True
        else:
            product.is_published = False
        if str(self.sheet[i][columns["canPublish"]]) == "TRUE":
            product.is_ca = True
        else:
            product.is_ca = False
        if str(self.sheet[i][columns["usPublish"]]) == "TRUE":
            product.is_us = True
        else:
            product.is_us = False

        if str(self.sheet[i][columns["canBeSold"]]) == "TRUE":
            product.sale_ok = True
        else:
            product.sale_ok = False

        product.active = True

        product.storeCode = self.sheet[i][columns["ecommerceWebsiteCode"]]
        product.type = "product"

        # Add translations to record
        product_sync_common.translatePricelist(
            self.database,
            product,
            self.sheet[i][columns["fName"]],
            self.sheet[i][columns["fDisc"]],
            "fr_CA",
        )
        product_sync_common.translatePricelist(
            self.database,
            product,
            self.sheet[i][columns["eName"]],
            self.sheet[i][columns["eDisc"]],
            "en_US",
        )
        if str(self.sheet[i][columns["type"]]) == "H":
            product.type_selection = "H"
        elif str(self.sheet[i][columns["type"]]) == "S":
            product.type_selection = "S"
        elif str(self.sheet[i][columns["type"]]) == "SS":
            product.type_selection = "SS"
        elif str(self.sheet[i][columns["type"]]) == "":
            product.type_selection = False
        return product

    # creates record and updates it
    def createPricelistProducts(self, external_id, product_name):
        ext = self.database.env["ir.model.data"].create(
            {"name": external_id, "model": "product.template"}
        )[0]
        product = self.database.env["product.template"].create({"name": product_name})[
            0
        ]
        ext.res_id = product.id

        product.tracking = "serial"

        return product
