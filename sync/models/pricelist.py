# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models
from odoo.tools.translate import _
from odoo import models, fields, api


class sync_pricelist():
    def __init__(self, name, sheet, database):
        self.sheet = sheet
        self.database = database
        self.name = name

        # follows same pattern
    def syncPricelist(self, sheet):
        sheetWidth = 22
        i = 1

        columns = dict()
        columnsMissing = False

        if("SKU" in sheet[0]):
            columns["sku"] = sheet[0].index("SKU")
        else:
            columnsMissing = True

        if("EN-Name" in sheet[0]):
            columns["eName"] = sheet[0].index("EN-Name")
        else:
            columnsMissing = True

        if("EN-Description" in sheet[0]):
            columns["eDisc"] = sheet[0].index("EN-Description")
        else:
            columnsMissing = True

        if("FR-Name" in sheet[0]):
            columns["fName"] = sheet[0].index("FR-Name")
        else:
            columnsMissing = True

        if("FR-Description" in sheet[0]):
            columns["fDisc"] = sheet[0].index("FR-Description")
        else:
            columnsMissing = True

        if("Price" in sheet[0]):
            columns["canPrice"] = sheet[0].index("Price")
        else:
            columnsMissing = True

        if("USD Price" in sheet[0]):
            columns["usPrice"] = sheet[0].index("USD Price")
        else:
            columnsMissing = True

        if("Publish_CA" in sheet[0]):
            columns["canPublish"] = sheet[0].index("Publish_CA")
        else:
            columnsMissing = True

        if("Publish_USA" in sheet[0]):
            columns["usPublish"] = sheet[0].index("Publish_USA")
        else:
            columnsMissing = True

        if("Can_Be_Sold" in sheet[0]):
            columns["canBeSold"] = sheet[0].index("Can_Be_Sold")
        else:
            columnsMissing = True

        if("E-Commerce_Website_Code" in sheet[0]):
            columns["ecommerceWebsiteCode"] = sheet[0].index(
                "E-Commerce_Website_Code")
        else:
            columnsMissing = True

        if("CAN PL SEL" in sheet[0]):
            columns["canPricelist"] = sheet[0].index("CAN PL SEL")
        else:
            columnsMissing = True

        if("CAN PL ID" in sheet[0]):
            columns["canPLID"] = sheet[0].index("CAN PL ID")
        else:
            columnsMissing = True

        if("USD PL SEL" in sheet[0]):
            columns["usPricelist"] = sheet[0].index("USD PL SEL")
        else:
            columnsMissing = True

        if("US PL ID" in sheet[0]):
            columns["usPLID"] = sheet[0].index("US PL ID")
        else:
            columnsMissing = True

        if("Continue" in sheet[0]):
            columns["continue"] = sheet[0].index("Continue")
        else:
            columnsMissing = True

        if("Valid" in sheet[0]):
            columns["valid"] = sheet[0].index("Valid")
        else:
            columnsMissing = True

        if(len(sheet[i]) != sheetWidth or columnsMissing):
            msg = "<h1>Pricelist page Invalid</h1>\n<p>Sheet width is: " + \
                str(len(sheet[i])) + "</p>"
            self.sendSyncReport(msg)
            _logger.info("Sheet Width: " + str(len(sheet[i])))
            return True, msg
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(i == len(sheet) or str(sheet[i][columns["continue"]]) != "TRUE"):
                break
            if(str(sheet[i][columns["valid"]]) != "TRUE"):
                i = i + 1
                continue

            if(not self.check_id(str(sheet[i][columns["sku"]]))):
                # msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_id(str(sheet[i][columns["canPLID"]]))):
                # msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_id(str(sheet[i][columns["usPLID"]]))):
                # msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_price(sheet[i][columns["canPrice"]])):
                # msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_price(sheet[i][columns["usPrice"]])):
                # msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue

            try:
                product, new = self.pricelistProduct(
                    sheet, sheetWidth, i, columns)
                if(product.stringRep == str(sheet[i][:])):
                    i = i + 1
                    continue

                self.pricelistCAN(product, sheet, sheetWidth, i, columns)
                self.pricelistUS(product, sheet, sheetWidth, i, columns)

                if(new):
                    _logger.info("Blank StringRep")
                    product.stringRep = ""
                else:
                    _logger.info("Pricelist Price StringRep")
                    product.stringRep = str(sheet[i][:])
            except Exception as e:
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                return True, msg

            i = i + 1
        # msg = self.endTable(msg)
        return False, msg

    def pricelistProduct(self, sheet, sheetWidth, i, columns):
        external_id = str(sheet[i][columns["sku"]])
        product_ids = self.database.env['ir.model.data'].search(
            [('name', '=', external_id), ('model', '=', 'product.template')])
        if(len(product_ids) > 0):
            return self.updatePricelistProducts(self.database.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i, columns), False
        else:
            return self.createPricelistProducts(sheet, external_id, sheetWidth, i, columns), True

    def pricelistCAN(self, product, sheet, sheetWidth, i, columns):
        external_id = str(sheet[i][columns["canPLID"]])
        pricelist_id = self.database.env['product.pricelist'].search(
            [('name', '=', 'CAN Pricelist')])[0].id
        pricelist_item_ids = self.database.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0):
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][columns["canPrice"]]) != " " and str(sheet[i][columns["canPrice"]]) != ""):
                pricelist_item.fixed_price = float(
                    sheet[i][columns["canPrice"]])
        else:
            pricelist_item = self.database.env['product.pricelist.item'].create(
                {'pricelist_id': pricelist_id, 'product_tmpl_id': product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][columns["canPrice"]]) != " " and str(sheet[i][columns["canPrice"]]) != ""):
                pricelist_item.fixed_price = sheet[i][columns["canPrice"]]

    def pricelistUS(self, product, sheet, sheetWidth, i, columns):
        external_id = str(sheet[i][columns["usPLID"]])
        pricelist_id = self.database.env['product.pricelist'].search(
            [('name', '=', 'USD Pricelist')])[0].id
        pricelist_item_ids = self.database.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0):
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][columns["usPrice"]]) != " " and str(sheet[i][columns["usPrice"]]) != ""):
                pricelist_item.fixed_price = sheet[i][columns["usPrice"]]

        else:
            pricelist_item = self.database.env['product.pricelist.item'].create(
                {'pricelist_id': pricelist_id, 'product_tmpl_id': product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][columns["usPrice"]]) != " " and str(sheet[i][columns["usPrice"]]) != ""):
                pricelist_item.fixed_price = sheet[i][columns["usPrice"]]

    def updatePricelistProducts(self, product, sheet, sheetWidth, i, columns, new=False):

        if(product.stringRep == str(sheet[i][:]) and product.stringRep != ""):
            return product

        product.name = sheet[i][columns["eName"]]
        product.description_sale = sheet[i][columns["eDisc"]]

        if(str(sheet[i][columns["canPrice"]]) != " " and str(sheet[i][columns["canPrice"]]) != ""):
            product.price = sheet[i][columns["canPrice"]]


#         _logger.info(str(sheet[i][7]))
#         if(len(str(sheet[i][7])) > 0):
#             url = str(sheet[i][7])
#             req = requests.get(url, stream=True)
#             if(req.status_code == 200):
#                 product.image_1920 = req.content

        if (str(sheet[i][columns["canPublish"]]) == "TRUE"):
            product.is_published = True
        else:
            product.is_published = False
        if (str(sheet[i][columns["canPublish"]]) == "TRUE"):
            product.is_ca = True
        else:
            product.is_ca = False
        if (str(sheet[i][columns["usPublish"]]) == "TRUE"):
            product.is_us = True
        else:
            product.is_us = False

        if(str(sheet[i][columns["canBeSold"]]) == "TRUE"):
            product.sale_ok = True
        else:
            product.sale_ok = False

        product.storeCode = sheet[i][columns["ecommerceWebsiteCode"]]
        product.tracking = "serial"
        product.type = "product"

        if(not new):
            _logger.info("Translate")
            self.translatePricelist(
                product, sheet, sheetWidth, i, columns["fName"], columns["fDisc"], "fr_CA", new)
            self.translatePricelist(
                product, sheet, sheetWidth, i, columns["eName"], columns["eDisc"], "en_CA", new)
            self.translatePricelist(
                product, sheet, sheetWidth, i, columns["eName"], columns["eDisc"], "en_US", new)

        return product

    def translatePricelist(self, product, sheet, sheetWidth, i, nameI, descriptionI, lang, new):
        if(new == True):
            return
        else:
            product_name = self.database.env['ir.translation'].search([('res_id', '=', product.id),
                                                                       ('name', '=',
                                                                        'product.template,name'),
                                                                       ('lang', '=', lang)])
            if(len(product_name) > 0):
                product_name[-1].value = sheet[i][nameI]

            else:
                product_name_new = self.database.env['ir.translation'].create({'name': 'product.template,name',
                                                                               'lang': lang,
                                                                               'res_id': product.id})[0]
                product_name_new.value = sheet[i][nameI]

            product_description = self.database.env['ir.translation'].search([('res_id', '=', product.id),
                                                                              ('name', '=', 'product.template,description_sale'),
                                                                              ('lang', '=', lang)])

            if(len(product_description) > 0):
                product_description[-1].value = sheet[i][descriptionI]
            else:
                product_description_new = self.database.env['ir.translation'].create({'name': 'product.template,description_sale',
                                                                                      'lang': lang,
                                                                                      'res_id': product.id})[0]
                product_description_new.value = sheet[i][descriptionI]
            return

    def createPricelistProducts(self, sheet, external_id, sheetWidth, i, columns):
        ext = self.database.env['ir.model.data'].create(
            {'name': external_id, 'model': "product.template"})[0]
        product = self.database.env['product.template'].create(
            {'name': sheet[i][columns["eName"]]})[0]
        ext.res_id = product.id
        self.updatePricelistProducts(
            product, sheet, sheetWidth, i, columns, new=True)
        return product
