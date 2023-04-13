# -*- coding: utf-8 -*-

from .utilities import utilities
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo.tools.translate import _
from odoo import models

_logger = logging.getLogger(__name__)

SKIP_NO_CHANGE = True


class sync_ccp:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    # follows same pattern
    def syncCCP(self):

        sheetWidth = 11
        columns = dict()
        columnsMissing = False
        msg = ""

        if ("Owner ID" in self.sheet[0]):
            columns["ownerId"] = self.sheet[0].index("Owner ID")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header",
                                     "Owner Id Missing")
            columnsMissing = True

        if ("EID/SN" in self.sheet[0]):
            columns["eidsn"] = self.sheet[0].index("EID/SN")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "EID/SN Missing")
            columnsMissing = True

        if ("External ID" in self.sheet[0]):
            columns["externalId"] = self.sheet[0].index("External ID")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "External ID Missing")
            columnsMissing = True

        if ("Product Code" in self.sheet[0]):
            columns["code"] = self.sheet[0].index("Product Code")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Product Code Missing")
            columnsMissing = True

        if ("Product Name" in self.sheet[0]):
            columns["name"] = self.sheet[0].index("Product Name")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Product Name Missing")
            columnsMissing = True

        if ("Publish" in self.sheet[0]):
            columns["publish"] = self.sheet[0].index("Product Name")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Publish Missing")
            columnsMissing = True

        if ("Expiration Date" in self.sheet[0]):
            columns["date"] = self.sheet[0].index("Expiration Date")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Expiration Date Missing")
            columnsMissing = True

        if ("Valid" in self.sheet[0]):
            columns["valid"] = self.sheet[0].index("Valid")
        else:
            msg = utilities.buildMSG(msg, self.name, "Header", "Valid Missing")
            columnsMissing = True

        if ("Continue" in self.sheet[0]):
            columns["continue"] = self.sheet[0].index("Continue")
        else:
            msg = utilities.buildMSG(
                msg, self.name, "Header", "Continue Missing")
            columnsMissing = True

        i = 1
        if (len(self.sheet[i]) != sheetWidth or columnsMissing):
            msg = "<h1>CCP page Invalid</h1>\n<p>" + str(self.name) + " width is: " + \
                str(len(self.sheet[i])) + " Expected " + \
                str(sheetWidth) + "</p>\n" + msg
            self.database.sendSyncReport(msg)
            _logger.info("self.sheet Width: " + str(len(self.sheet[i])))
            return True, msg
        r = ""
        msg = ""
        # msg = self.startTable(msg, self.sheet, sheetWidth)
        while (True):
            if (i == len(self.sheet) or str(self.sheet[i][columns["continue"]]) != "TRUE"):
                break
            if (str(self.sheet[i][columns["valid"]]) != "TRUE"):
                i = i + 1
                continue

            if (not utilities.check_id(str(self.sheet[i][columns["externalId"]]))):
                msg = utilities.buildMSG(
                    msg, self.name, "Header", "Invalid SKU")
                i = i + 1
                continue

            if (not utilities.check_date(str(self.sheet[i][columns["date"]]))):
                msg = utilities.buildMSG(
                    msg, self.name, str(
                        self.sheet[i][columns["externalId"]]), "Invalid Expiration Date: " + str(self.sheet[i][columns["date"]])
                )
                i = i + 1
                continue

            try:
                external_id = str(self.sheet[i][columns["externalId"]])

                ccp_ids = self.database.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'stock.production.lot')])
                if (len(ccp_ids) > 0):
                    self.updateCCP(self.database.env['stock.production.lot'].browse(
                        ccp_ids[-1].res_id), i, columns)
                else:
                    self.createCCP(external_id, i, columns)
            except Exception as e:
                _logger.info("CCP")
                _logger.error(e)
                _logger.info(i)
                msg = utilities.buildMSG(
                    msg, self.name, str(external_id), str(e))
                msg = msg + str(e)
                return True, msg
            i = i + 1

        return False, msg

    # follows same pattern
    def updateCCP(self, ccp_item, i, columns):
        if (ccp_item.stringRep == str(self.sheet[i][:])):
            return

        ccp_item.name = self.sheet[i][columns["eidsn"]]

        product_ids = self.database.env['product.product'].search(
            [('sku', '=', self.sheet[i][columns["code"]])])

        ccp_item.product_id = product_ids[-1].id

        owner_ids = self.database.env['ir.model.data'].search(
            [('name', '=', self.sheet[i][columns["ownerId"]]), ('model', '=', 'res.partner')])
        if (len(owner_ids) == 0):
            _logger.info("No owner")

        ccp_item.owner = owner_ids[-1].res_id
        if (self.sheet[i][columns["date"]] != "FALSE"):
            ccp_item.expire = self.sheet[i][columns["date"]]
        else:
            ccp_item.expire = None

        ccp_item.publish = self.sheet[i][columns["publish"]]

        ccp_item.stringRep = str(self.sheet[i][:])

    # follows same pattern
    def createCCP(self, external_id, i, columns):
        ext = self.database.env['ir.model.data'].create(
            {'name': external_id, 'model': "stock.production.lot"})[0]

        product_ids = self.database.env['product.product'].search(
            [('name', '=', self.sheet[i][columns["name"]])])

        product_id = product_ids[len(product_ids) - 1].id

        company_id = self.database.env['res.company'].search(
            [('id', '=', 1)]).id

        ccp_item = self.database.env['stock.production.lot'].create({'name': self.sheet[i][columns["eidsn"]],
                                                                     'product_id': product_id, 'company_id': company_id})[0]
        ext.res_id = ccp_item.id
        self.updateCCP(ccp_item, i, columns)
