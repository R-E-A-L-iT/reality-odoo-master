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

        sheetWidth = 9

        columns = dict()
        columnsMissing = False

        if ("Owner ID" in self.sheet[0]):
            columns["ownerId"] = self.sheet[0].index("Owner ID")
        else:
            columnsMissing = True

        if ("EID/SN" in self.sheet[0]):
            columns["eidsn"] = self.sheet[0].index("EID/SN")
        else:
            columnsMissing = True

        if ("External ID" in self.sheet[0]):
            columns["externalId"] = self.sheet[0].index("External ID")
        else:
            columnsMissing = True

        if ("Product Code" in self.sheet[0]):
            columns["code"] = self.sheet[0].index("Product Code")
        else:
            columnsMissing = True

        if ("Product Name" in self.sheet[0]):
            columns["name"] = self.sheet[0].index("Product Name")
        else:
            columnsMissing = True

        if ("Expiration Date" in self.sheet[0]):
            columns["date"] = self.sheet[0].index("Expiration Date")
        else:
            columnsMissing = True

        if ("Valid" in self.sheet[0]):
            columns["valid"] = self.sheet[0].index("Valid")
        else:
            columnsMissing = True

        if ("Continue" in self.sheet[0]):
            columns["continue"] = self.sheet[0].index("Continue")
        else:
            columnsMissing = True

        i = 1
        if (len(self.sheet[i]) != sheetWidth or columnsMissing):
            msg = "<h1>Sync Page Invalid<h1>\n<h2>syncCCP function</h2>"
            self.sendSyncReport(msg)
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

            try:
                external_id = str(self.sheet[i][columns["externalId"]])

                ccp_ids = self.database['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'stock.production.lot')])
                if (len(ccp_ids) > 0):
                    self.updateCCP(self.database['stock.production.lot'].browse(
                        ccp_ids[-1].res_id), self.sheet, sheetWidth, i, columns)
                else:
                    self.createCCP(external_id,
                                   sheetWidth, i, columns)
            except Exception as e:
                _logger.info("CCP")
                _logger.info(e)
                _logger.info(i)
                msg = utilities.buildMSG(
                    msg, self.name, str(external_id), str(e))
                msg = msg + str(e)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg

    # follows same pattern
    def updateCCP(self, ccp_item, i, columns):
        if (ccp_item.stringRep == str(self.sheet[i][:])):
            return

#         if(i == 8):
        # _logger.info("name")
        ccp_item.name = self.sheet[i][columns["eidsn"]]

#         if(i == 8):
        # _logger.info("id")
        product_ids = self.database['product.product'].search(
            [('name', '=', self.sheet[i][columns["name"]])])
        # _logger.info(str(len(product_ids)))
        # _logger.info(str(self.sheet[i][columns["name"]]))

#         if(i == 8):
        # _logger.info("Id Tupple")
        ccp_item.product_id = product_ids[-1].id


#         if(i == 8):
        # _logger.info("owner")
        owner_ids = self.database['ir.model.data'].search(
            [('name', '=', self.sheet[i][columns["ownerId"]]), ('model', '=', 'res.partner')])
        if (len(owner_ids) == 0):
            _logger.info("No owner")


#         if(i == 8):
        # _logger.info("Owner Tupple")
        ccp_item.owner = owner_ids[-1].res_id
        if (self.sheet[i][columns["date"]] != "FALSE"):
            ccp_item.expire = self.sheet[i][columns["date"]]
        else:
            ccp_item.expire = None

        # _logger.info("CCP String Rep")
        ccp_item.stringRep = str(self.sheet[i][:])

    # follows same pattern
    def createCCP(self, external_id, sheetWidth, i, columns):
        ext = self.database['ir.model.data'].create(
            {'name': external_id, 'model': "stock.production.lot"})[0]

        product_ids = self.database['product.product'].search(
            [('name', '=', self.sheet[i][columns["name"]])])

        product_id = product_ids[len(product_ids) - 1].id

        company_id = self.database['res.company'].search([('id', '=', 1)]).id

        ccp_item = self.database['stock.production.lot'].create({'name': self.sheet[i][columns["eidsn"]],
                                                                 'product_id': product_id, 'company_id': company_id})[0]
        ext.res_id = ccp_item.id
        self.updateCCP(ccp_item, sheetWidth, i, columns)
