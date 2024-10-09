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

    def syncCCP(self):
        # Confirm GS Tab is in the correct Format
        sheetWidth = 11
        columns = dict()
        columnsMissing = False
        msg = ""
        i = 1

        # Check if the header match the appropriate format
        ccpHeaderDict = dict()
        ccpHeaderDict["Owner ID"]           = "ownerId"
        ccpHeaderDict["EID/SN"]             = "eidsn"
        ccpHeaderDict["External ID"]        = "externalId"
        ccpHeaderDict["Product Code"]       = "code"
        ccpHeaderDict["Product Name"]       = "name"
        ccpHeaderDict["Publish"]            = "publish"
        ccpHeaderDict["Expiration Date"]    = "date"
        ccpHeaderDict["Valid"]              = "valid"
        ccpHeaderDict["Continue"]           = "continue"
        columns, msg, columnsMissing = utilities.checkSheetHeader(ccpHeaderDict, self.sheet, self.name)

        
        if len(self.sheet[i]) != sheetWidth or columnsMissing:
            msg = (
                "<h1>CCP page Invalid</h1>\n<p>"
                + str(self.name)
                + " width is: "
                + str(len(self.sheet[i]))
                + " Expected "
                + str(sheetWidth)
                + "</p>\n"
                + msg
            )
            self.database.sendSyncReport(msg)
            _logger.info("self.sheet Width: " + str(len(self.sheet[i])))
            return True, msg

        # Loop through Rows in Google Sheets        
        while True:
            # Check if final row was completed
            if (i == len(self.sheet) or 
                str(self.sheet[i][columns["continue"]]) != "TRUE"):
                break

            # Verify The validity of certain fields
            if str(self.sheet[i][columns["valid"]]) != "TRUE":
                i = i + 1
                continue

            if not utilities.check_id(str(self.sheet[i][columns["externalId"]])):
                msg = utilities.buildMSG(msg, self.name, "Header", "Invalid SKU")
                i = i + 1
                continue

            if not utilities.check_date(str(self.sheet[i][columns["date"]])):
                msg = utilities.buildMSG(
                    msg,
                    self.name,
                    str(self.sheet[i][columns["externalId"]]),
                    "Invalid Expiration Date: " + str(self.sheet[i][columns["date"]]))
                i = i + 1
                continue

            try:                
                # Create or Update record as needed
                external_id = str(self.sheet[i][columns["externalId"]])
                ccp_ids = self.database.env["ir.model.data"].search(
                    [("name", "=", external_id), 
                     ("model", "=", "stock.lot")])
                
                if len(ccp_ids) > 0:
                    self.updateCCP(
                        self.database.env["stock.lot"].browse(ccp_ids[-1].res_id),
                        i,
                        columns)
                else:
                    self.createCCP(external_id, i, columns)

            except Exception as e:
                _logger.info("CCP")
                _logger.error(e)
                _logger.exception(e)
                _logger.info(str(self.sheet[i]))
                msg = utilities.buildMSG(msg, self.name, str(external_id), str(e))
                msg = msg + str(e)
                return True, msg

            i = i + 1
        return False, msg

    def updateCCP(self, ccp_item, i, columns):
        # Check if data in GS is the same as in Odoo
        if ccp_item.stringRep == str(self.sheet[i][:]):
            return
            
        # Update fields in Record
        ccp_item.name = self.sheet[i][columns["eidsn"]]

        product_ids = self.database.env["product.product"].search(
            [("sku", "=", self.sheet[i][columns["code"]])])

        ccp_item.product_id = product_ids[-1].id

        owner_ids = self.database.env["ir.model.data"].search([
                ("name", "=", self.sheet[i][columns["ownerId"]]),
                ("model", "=", "res.partner")])
        if len(owner_ids) == 0:
            _logger.info("No owner")

        ccp_item.owner = owner_ids[-1].res_id
        if self.sheet[i][columns["date"]] != "FALSE":
            ccp_item.expire = self.sheet[i][columns["date"]]
        else:
            ccp_item.expire = None

        ccp_item.publish = self.sheet[i][columns["publish"]]

        ccp_item.stringRep = str(self.sheet[i][:])

    # follows same pattern
    def createCCP(self, external_id, i, columns):
        # Create new record
        ext = self.database.env["ir.model.data"].create({"name": external_id, "model": "stock.lot"})[0]
        product_ids = self.database.env["product.product"].search([("sku", "=", self.sheet[i][columns["code"]])])
        product_id = product_ids[len(product_ids) - 1].id        
        company_id = self.database.env["res.company"].search([("id", "=", 1)]).id

        ccp_item = self.database.env["stock.lot"].create({
                "name": self.sheet[i][columns["eidsn"]],
                "product_id": product_id,
                "company_id": company_id,
            })[0]
        ext.res_id = ccp_item.id

        self.updateCCP(ccp_item, i, columns)

