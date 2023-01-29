# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

from .pricelist import sync_pricelist
_logger = logging.getLogger(__name__)

SKIP_NO_CHANGE = True


class sync_products():
    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def syncProducts(self, sheet):

        sheetWidth = 9
        i = 1

        columns = dict()
        columnsMissing = ""

        if ("SKU" in sheet[0]):
            columns["sku"] = sheet[0].index("SKU")
        else:
            columnsMissing = "SKU"

        if ("Name" in sheet[0]):
            columns["name"] = sheet[0].index("Name")
        else:
            columnsMissing = "Name"

        if ("Description" in sheet[0]):
            columns["description"] = sheet[0].index("Description")
        else:
            columnsMissing = "Description"

        if ("Price CAD" in sheet[0]):
            columns["priceCAD"] = sheet[0].index("Price CAD")
        else:
            columnsMissing = "Price CAD"

        if ("Price USD" in sheet[0]):
            columns["priceUSD"] = sheet[0].index("Price USD")
        else:
            columnsMissing = "Price USD"

        if ("Product Type" in sheet[0]):
            columns["type"] = sheet[0].index("Product Type")
        else:
            columnsMissing = "Product Type"

        if ("Tracking" in sheet[0]):
            columns["tracking"] = sheet[0].index("Tracking")
        else:
            columnsMissing = "Tracking"

        if ("Valid" in sheet[0]):
            columns["valid"] = sheet[0].index("Valid")
        else:
            columnsMissing = "Valid"

        if ("Continue" in sheet[0]):
            columns["continue"] = sheet[0].index("Continue")
        else:
            columnsMissing = "Continue"

        if (sheetWidth != len(sheet[i]) or columnsMissing != ""):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)

            if (sheetWidth != len(sheet[i])):
                _logger.info("Sheet Width: " + str(len(sheet[i])))

            if (columnsMissing != ""):
                _logger.info("columnsMissing: " + columnsMissing)

            return True, msg

        r = ""
        msg = ""
        while (True):

            #_logger.info("sheet[i][:]: " + str(sheet[i][:]))

            if (str(sheet[i][columns["continue"]]).upper() != "TRUE"):
                break

            # Primary Key used in Google Sheet Database
            key = str(sheet[i][columns["sku"]])
            if (not utilities.check_id(key)):
                msg = utilities.buildMSG(
                    msg, self.name, key, "Key Error")
                i += 1
                continue

            if (not utilities.check_price(sheet[i][columns["priceCAD"]])):
                msg = utilities.buildMSG(
                    msg, self.name, key, "CAD Price Invalid")
                i += 1
                continue

            if (not utilities.check_price(sheet[i][columns["priceUSD"]])):
                msg = utilities.buildMSG(
                    msg, self.name, key, "USD Price Invalid")
                i += 1
                continue

            try:
                external_id = str(sheet[i][columns["sku"]])
                product_ids = self.database.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'product.template')])

                if (len(product_ids) > 0):
                    _logger.info("Update Existing CCP Product")
                    product = self.database.env['product.template'].browse(
                        product_ids[len(product_ids) - 1].res_id)
                    self.updateProducts(
                        product,
                        str(sheet[i][:]),  # product_stringRep
                        sheet[i][columns["name"]],  # product_name
                        # product_description_sale
                        sheet[i][columns["description"]],
                        sheet[i][columns["priceCAD"]],  # product_price_cad
                        sheet[i][columns["priceUSD"]],  # product_price_usd
                        "serial",  # product_tracking
                        "product")  # product_type
                else:
                    _logger.info("Create new CCP product")
                    self.createAndUpdateProducts(
                        external_id,
                        str(sheet[i][:]),  # product_stringRep
                        sheet[i][columns["name"]],  # product_name
                        # product_description_sale
                        sheet[i][columns["description"]],
                        sheet[i][columns["priceCAD"]],  # product_price_cad
                        sheet[i][columns["priceUSD"]],  # product_price_usd
                        "serial",  # product_tracking
                        "product")  # product_type

            except Exception as e:
                _logger.info("Products Exception")
                _logger.info(e)
                msg = utilities.buildMSG(msg, self.name, key, str(e))
                return True, msg

            i += 1

        msg = self.endTable(msg)
        return False, msg

    # Method to create a product
    # Input
    #   external_id:    The external id, wich is the SKU key in the GoogleSheet Database.
    #   product_name:   Name of the product
    # Output
    #   product:        The product generated by Odoo

    def createProducts(self, external_id, product_name):
        product = None
        ext = self.database.env['ir.model.data'].create(
            {'name': external_id, 'model': "product.template"})[0]
        product = self.database.env['product.template'].create(
            {'name': product_name})[0]

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
            product_name,
            product_description_sale,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type):

        if (product.stringRep == product_stringRep):
            return

        product.name = product_name
        product.description_sale = product_description_sale
        product.tracking = product_tracking
        product.type = product_type
        product.stringRep = product_stringRep
        # pricelist need to be done before modifiyng the product.price
        # since it will be erased be the addProductToPricelist.  Apparently,
        # Odoo set to price to 0 if we set the product in a pricelist.
        syncer = sync_pricelist(self.name, self.sheet, self.database)
        syncer.addProductToPricelist(
            product, "CAN Pricelist", product_price_cad)
        syncer.addProductToPricelist(
            product, "USD Pricelist", product_price_usd)
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
            product_name,
            product_description_sale,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type):

        product = self.createProducts(external_id, product_name)
        self.updateProducts(
            product,
            product_stringRep,
            product_name,
            product_description_sale,
            product_price_cad,
            product_price_usd,
            product_tracking,
            product_type)

        product_created = self.database.env['product.template'].search(
            [('sku', '=', external_id)])
        return product_created
