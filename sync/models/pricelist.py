# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)


class sync_pricelist:

    def __init__(self, name, sheet):
        self.name = name
        self.sheet = sheet

# follows same pattern
    def syncPricelist(self):
        sheetWidth = 22
        i = 1

        columns = dict()
        columnsMissing = False

        if("SKU" in self.sheet[0]):
            columns["sku"] = self.sheet[0].index("SKU")
        else:
            columnsMissing = True

        if("EN-Name" in self.sheet[0]):
            columns["eName"] = self.sheet[0].index("EN-Name")
        else:
            columnsMissing = True

        if("EN-Description" in self.sheet[0]):
            columns["eDisc"] = self.sheet[0].index("EN-Description")
        else:
            columnsMissing = True

        if("FR-Name" in self.sheet[0]):
            columns["fName"] = self.sheet[0].index("FR-Name")
        else:
            columnsMissing = True

        if("FR-Description" in self.sheet[0]):
            columns["fDisc"] = self.sheet[0].index("FR-Description")
        else:
            columnsMissing = True

        if("Price" in self.sheet[0]):
            columns["canPrice"] = self.sheet[0].index("Price")
        else:
            columnsMissing = True

        if("USD Price" in self.sheet[0]):
            columns["usPrice"] = self.sheet[0].index("USD Price")
        else:
            columnsMissing = True

        if("Publish_CA" in self.sheet[0]):
            columns["canPublish"] = self.sheet[0].index("Publish_CA")
        else:
            columnsMissing = True

        if("Publish_USA" in self.sheet[0]):
            columns["usPublish"] = self.sheet[0].index("Publish_USA")
        else:
            columnsMissing = True

        if("Can_Be_Sold" in self.sheet[0]):
            columns["canBeSold"] = self.sheet[0].index("Can_Be_Sold")
        else:
            columnsMissing = True

        if("E-Commerce_Website_Code" in self.sheet[0]):
            columns["ecommerceWebsiteCode"] = self.sheet[0].index(
                "E-Commerce_Website_Code")
        else:
            columnsMissing = True

        if("CAN PL SEL" in self.sheet[0]):
            columns["canPricelist"] = self.sheet[0].index("CAN PL SEL")
        else:
            columnsMissing = True

        if("CAN PL ID" in self.sheet[0]):
            columns["canPLID"] = self.sheet[0].index("CAN PL ID")
        else:
            columnsMissing = True

        if("USD PL SEL" in self.sheet[0]):
            columns["usPricelist"] = self.sheet[0].index("USD PL SEL")
        else:
            columnsMissing = True

        if("US PL ID" in self.sheet[0]):
            columns["usPLID"] = self.sheet[0].index("US PL ID")
        else:
            columnsMissing = True

        if("Continue" in self.sheet[0]):
            columns["continue"] = self.sheet[0].index("Continue")
        else:
            columnsMissing = True

        if("Valid" in self.sheet[0]):
            columns["valid"] = self.sheet[0].index("Valid")
        else:
            columnsMissing = True

        if(len(self.sheet[i]) != sheetWidth or columnsMissing):
            msg = "<h1>Pricelist page Invalid</h1>\n<p>self.sheet width is: " + \
                str(len(self.sheet[i])) + "</p>"
            self.sendSyncReport(msg)
            _logger.info("self.sheet Width: " + str(len(self.sheet[i])))
            return True, msg
        r = ""
        msg = ""
        # msg = self.startTable(msg, sheetWidth)
        while(True):
            if(i == len(self.sheet) or str(self.sheet[i][columns["continue"]]) != "TRUE"):
                break
            if(str(self.sheet[i][columns["valid"]]) != "TRUE"):
                i = i + 1
                continue

            if(not self.check_id(str(self.sheet[i][columns["sku"]]))):
                # msg = self.buildMSG(msg, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_id(str(self.sheet[i][columns["canPLID"]]))):
                # msg = self.buildMSG(msg, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_id(str(self.sheet[i][columns["usPLID"]]))):
                # msg = self.buildMSG(msg, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_price(self.sheet[i][columns["canPrice"]])):
                # msg = self.buildMSG(msg, sheetWidth, i)
                i = i + 1
                continue

            if(not self.check_price(self.sheet[i][columns["usPrice"]])):
                # msg = self.buildMSG(msg, sheetWidth, i)
                i = i + 1
                continue

            try:
                product, new = self.pricelistProduct(
                    sheetWidth, i, columns)
                if(product.stringRep == str(self.sheet[i][:])):
                    i = i + 1
                    continue

                self.pricelistCAN(product, sheetWidth, i, columns)
                self.pricelistUS(product, sheetWidth, i, columns)

                if(new):
                    _logger.info("Blank StringRep")
                    product.stringRep = ""
                else:
                    _logger.info("Pricelist Price StringRep")
                    product.stringRep = str(self.sheet[i][:])
            except Exception as e:
                _logger.info(e)
                msg = self.buildMSG(msg, sheetWidth, i)
                return True, msg

            i = i + 1
        # msg = self.endTable(msg)
        return False, msg

    def pricelistProduct(self, sheetWidth, i, columns):
        external_id = str(self.sheet[i][columns["sku"]])
        product_ids = self.env['ir.model.data'].search(
            [('name', '=', external_id), ('model', '=', 'product.template')])
        if(len(product_ids) > 0):
            return self.updatePricelistProducts(self.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheetWidth, i, columns), False
        else:
            return self.createPricelistProducts(external_id, sheetWidth, i, columns), True

    def pricelistCAN(self, product, sheetWidth, i, columns):
        external_id = str(self.sheet[i][columns["canPLID"]])
        pricelist_id = self.env['product.pricelist'].search(
            [('name', '=', 'CAN Pricelist')])[0].id
        pricelist_item_ids = self.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0):
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(self.sheet[i][columns["canPrice"]]) != " " and str(self.sheet[i][columns["canPrice"]]) != ""):
                pricelist_item.fixed_price = float(
                    self.sheet[i][columns["canPrice"]])
        else:
            pricelist_item = self.env['product.pricelist.item'].create(
                {'pricelist_id': pricelist_id, 'product_tmpl_id': product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(self.sheet[i][columns["canPrice"]]) != " " and str(self.sheet[i][columns["canPrice"]]) != ""):
                pricelist_item.fixed_price = self.sheet[i][columns["canPrice"]]

    def pricelistUS(self, product, sheetWidth, i, columns):
        external_id = str(self.sheet[i][columns["usPLID"]])
        pricelist_id = self.env['product.pricelist'].search(
            [('name', '=', 'USD Pricelist')])[0].id
        pricelist_item_ids = self.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0):
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(self.sheet[i][columns["usPrice"]]) != " " and str(self.sheet[i][columns["usPrice"]]) != ""):
                pricelist_item.fixed_price = self.sheet[i][columns["usPrice"]]

        else:
            pricelist_item = self.env['product.pricelist.item'].create(
                {'pricelist_id': pricelist_id, 'product_tmpl_id': product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(self.sheet[i][columns["usPrice"]]) != " " and str(self.sheet[i][columns["usPrice"]]) != ""):
                pricelist_item.fixed_price = self.sheet[i][columns["usPrice"]]

    def updatePricelistProducts(self, product, sheetWidth, i, columns, new=False):

        if(product.stringRep == str(self.sheet[i][:]) and product.stringRep != ""):
            return product

        product.name = self.sheet[i][columns["eName"]]
        product.description_sale = self.sheet[i][columns["eDisc"]]

        if(str(self.sheet[i][columns["canPrice"]]) != " " and str(self.sheet[i][columns["canPrice"]]) != ""):
            product.price = self.sheet[i][columns["canPrice"]]


#         _logger.info(str(self.sheet[i][7]))
#         if(len(str(self.sheet[i][7])) > 0):
#             url = str(self.sheet[i][7])
#             req = requests.get(url, stream=True)
#             if(req.status_code == 200):
#                 product.image_1920 = req.content

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

        if(str(self.sheet[i][columns["canBeSold"]]) == "TRUE"):
            product.sale_ok = True
        else:
            product.sale_ok = False

        product.storeCode = self.sheet[i][columns["ecommerceWebsiteCode"]]
        product.tracking = "serial"
        product.type = "product"

        if(not new):
            _logger.info("Translate")
            self.translatePricelist(
                product, sheetWidth, i, columns["fName"], columns["fDisc"], "fr_CA", new)
            self.translatePricelist(
                product, sheetWidth, i, columns["eName"], columns["eDisc"], "en_CA", new)
            self.translatePricelist(
                product, sheetWidth, i, columns["eName"], columns["eDisc"], "en_US", new)

        return product

    def translatePricelist(self, product, sheetWidth, i, nameI, descriptionI, lang, new):
        if(new == True):
            return
        else:
            product_name = self.env['ir.translation'].search([('res_id', '=', product.id),
                                                              ('name', '=',
                                                               'product.template,name'),
                                                              ('lang', '=', lang)])
            if(len(product_name) > 0):
                product_name[-1].value = self.sheet[i][nameI]

            else:
                product_name_new = self.env['ir.translation'].create({'name': 'product.template,name',
                                                                      'lang': lang,
                                                                      'res_id': product.id})[0]
                product_name_new.value = self.sheet[i][nameI]

            product_description = self.env['ir.translation'].search([('res_id', '=', product.id),
                                                                     ('name', '=', 'product.template,description_sale'),
                                                                     ('lang', '=', lang)])

            if(len(product_description) > 0):
                product_description[-1].value = self.sheet[i][descriptionI]
            else:
                product_description_new = self.env['ir.translation'].create({'name': 'product.template,description_sale',
                                                                             'lang': lang,
                                                                             'res_id': product.id})[0]
                product_description_new.value = self.sheet[i][descriptionI]
            return

    def createPricelistProducts(self, external_id, sheetWidth, i, columns):
        ext = self.env['ir.model.data'].create(
            {'name': external_id, 'model': "product.template"})[0]
        product = self.env['product.template'].create(
            {'name': self.sheet[i][columns["eName"]]})[0]
        ext.res_id = product.id
        self.updatePricelistProducts(
            product, sheetWidth, i, columns, new=True)
        return product
