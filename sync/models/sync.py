# -*- coding: utf-8 -*-

import ast
import logging
import json
import re

import requests
import werkzeug.urls
import base64

from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT, TIMEOUT
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import RedirectWarning, AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.tools.translate import _
from odoo import models, fields, api

from .pricelist import sync_pricelist
from .ccp import sync_ccp

_logger = logging.getLogger(__name__)


class sync(models.Model):
    _name = "sync.sync"

    _inherit = "sync.sheets"

    DatabaseURL = fields.Char(default="")

    _description = "Sync App"

    # STARTING POINT
    def start_sync(self, psw=None):
        _logger.info("Starting Sync")

        # Checks authentication values
        if (psw == None):
            msg = "<h1>Sync Error</h1><p>Authentication values Missing</p>"
            _logger.info(msg)
            self.sendSyncReport(msg)
            return

        # next funct
        self.getSyncData(psw)
        _logger.info("Ending Sync")

    def getSyncData(self, psw):

        # DEV R-E-A-L.iT Master Database
        template_id = "17qHJGr_dhUm7B_hKYuKS32nQ1-5iIWBqVhtkHOEb5ls"
        
        # R-E-A-L.iT Master Database
        #template_id = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"

        # get the database data; reading in the sheet
        try:
            sync_data = self.getDoc(psw, template_id, 0)
        except Exception as e:
            _logger.info(e)
            msg = "<h1>Source Document Invalid</h1><p>Sync Fail</p>"
            self.sendSyncReport(msg)
            return

        i = 1
        sheetIndex = ""
        syncType = ""
        msg = ""

        # loop through entries in first sheet
        while (True):
            sheetName   = str(sync_data[i][0])
            sheetIndex  = int(sync_data[i][1])
            syncType    = str(sync_data[i][2])
            validity    = str(sync_data[i][3])
            _logger.info("Valid: " + sheetName + " is " + validity)

            if (validity != "TRUE"):
                break

            quit, msgr = self.getSyncValues(sheetName,
                                            psw, template_id, sheetIndex, syncType)                                         
            msg = msg + msgr
            i += 1
           
            if (quit):
                self.syncCancel(msg)
                return

        # error
        if (msg != ""):
            self.syncFail(msg)

    def getSyncValues(self, sheetName, psw, template_id, sheetIndex, syncType):
        try:
            sheet = self.getDoc(psw, template_id, sheetIndex)
        except Exception as e:
            _logger.info(e)
            msg = (
                "<h1>Source Document Invalid<\h1><p>Page: %s</p><p>Sync Fail</p>" % sheetIndex)
            self.sendSyncReport(msg)
            return False, ""

        _logger.info("Sync Type is: " + syncType)    
        # identify the type of sheet        
        if (syncType == "Companies"):
            quit, msg = self.syncCompanies(sheet)
            
        elif (syncType == "Contacts"):
            quit, msg = self.syncContacts(sheet)
            
        elif (syncType == "Products"):
            quit, msg = self.syncProducts(sheet)
            
        elif (syncType == "CCP"):
            syncer = sync_ccp(sheetName, sheet, self)
            quit, msg = syncer.syncCCP()
            
        elif (syncType == "Pricelist"):
            # syncer = sync_pricelist.connect(sheetName, sheet, self)
            syncer = sync_pricelist(sheetName, sheet, self)
            quit, msg = syncer.syncPricelist()
            quit = False
            msg = ""
            # quit, msg = self.syncPricelist(sheet)
            
        elif (syncType == "WebHTML"):
            quit, msg = self.syncWebCode(sheet)

        _logger.info("Done with " + syncType)
        _logger.info("quit: " + str(quit) + "\n")
        _logger.info("msg:  " + str(msg))
        
        return quit, msg

    # same pattern for all sync items
    def syncCompanies(self, sheet):

        # check sheet width to filter out invalid sheets
        # every company tab will have the same amount of columns (Same with others)
        sheetWidth = 17
        columns = dict()
        missingColumn = False

        # Calculate Indexes
        if ("Company Name" in sheet[0]):
            columns["companyName"] = sheet[0].index("Company Name")
        else:
            missingColumn = True

        if ("Phone" in sheet[0]):
            columns["phone"] = sheet[0].index("Phone")
        else:
            missingColumn = True

        if ("Website" in sheet[0]):
            columns["website"] = sheet[0].index("Website")
        else:
            missingColumn = True

        if ("Street" in sheet[0]):
            columns["street"] = sheet[0].index("Street")
        else:
            missingColumn = True

        if ("City" in sheet[0]):
            columns["city"] = sheet[0].index("City")
        else:
            missingColumn = True

        if ("State" in sheet[0]):
            columns["state"] = sheet[0].index("State")
        else:
            missingColumn = True

        if ("Country Code" in sheet[0]):
            columns["country"] = sheet[0].index("Country Code")
        else:
            missingColumn = True

        if ("Postal Code" in sheet[0]):
            columns["postalCode"] = sheet[0].index("Postal Code")
        else:
            missingColumn = True

        if ("Language" in sheet[0]):
            columns["language"] = sheet[0].index("Language")
        else:
            missingColumn = True

        if ("Email" in sheet[0]):
            columns["email"] = sheet[0].index("Email")
        else:
            missingColumn = True

        if ("Pricelist" in sheet[0]):
            columns["pricelist"] = sheet[0].index("Pricelist")
        else:
            missingColumn = True

        if ("OCOMID" in sheet[0]):
            columns["id"] = sheet[0].index("OCOMID")
        else:
            missingColumn = True

        if ("Valid" in sheet[0]):
            columns["valid"] = sheet[0].index("Valid")
        else:
            missingColumn = True

        if ("Continue" in sheet[0]):
            columns["continue"] = sheet[0].index("Continue")
        else:
            missingColumn = True

        i = 1
        if (len(sheet[i]) != sheetWidth or missingColumn):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            _logger.info("Sheet Width: " + str(len(sheet[i])))
            return True, msg

        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)

        # loop through all the rows
        while (True):

            # check if should continue
            if (str(sheet[i][columns["continue"]]) != "TRUE"):
                break

            # validation checks (vary depending on tab/function)
            if (str(sheet[i][columns["valid"]]) != "TRUE"):
                _logger.info("Invalid")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            if (not self.check_id(str(sheet[i][columns["id"]]))):

                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            # if it gets here data should be valid
            try:

                # attempts to access existing item (item/row)
                external_id = str(sheet[i][columns["id"]])
                company_ids = self.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'res.partner')])
                if (len(company_ids) > 0):
                    self.updateCompany(self.env['res.partner'].browse(
                        company_ids[len(company_ids) - 1].res_id), sheet, sheetWidth, i, columns)
                else:
                    self.createCompany(sheet, external_id,
                                       sheetWidth, i, columns)
            except Exception as e:
                _logger.info("Companies")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i += 1
        msg = self.endTable(msg)
        return False, msg

    def updateCompany(self, company, sheet, sheetWidth, i, columns):

        # check if any update to item is needed and skips if there is none
        if (company.stringRep == str(sheet[i][:])):
            return

        # reads values and puts them in appropriate fields
        company.name = sheet[i][columns["companyName"]]
        company.phone = sheet[i][columns["phone"]]
        company.website = sheet[i][columns["website"]]
        company.street = sheet[i][columns["street"]]
        company.city = sheet[i][columns["city"]]
        if (sheet[i][columns["state"]] != ""):
            stateTup = self.env['res.country.state'].search(
                [('code', '=', sheet[i][columns["state"]])])
            if (len(stateTup) > 0):
                company.state_id = int(stateTup[0].id)
        name = sheet[i][columns["country"]]
        if (name != ""):
            if (name == "US"):
                name = "United States"
            company.country_id = int(
                self.env['res.country'].search([('name', '=', name)])[0].id)
        company.zip = sheet[i][columns["postalCode"]]
        company.lang = sheet[i][columns["language"]]
        company.email = sheet[i][columns["language"]]
        if (sheet[i][columns["pricelist"]] != ""):
            company.property_product_pricelist = int(self.env['product.pricelist'].search(
                [('name', '=', sheet[i][columns["pricelist"]])])[0].id)
        company.is_company = True

        _logger.info("Company StringRep")
        company.stringRep = str(sheet[i][:])

    # creates object and updates it
    def createCompany(self, sheet, external_id, sheetWidth, i, columns):
        ext = self.env['ir.model.data'].create(
            {'name': external_id, 'model': "res.partner"})[0]
        company = self.env['res.partner'].create(
            {'name': sheet[i][columns["companyName"]]})[0]
        ext.res_id = company.id
        self.updateCompany(company, sheet, sheetWidth, i, columns)

    # follows same pattern
    def syncContacts(self, sheet):

        sheetWidth = 17
        columns = dict()
        columnsMissing = False

        if ("Name" in sheet[0]):
            columns["name"] = sheet[0].index("Name")
        else:
            columnsMissing = True

        if ("Phone" in sheet[0]):
            columns["phone"] = sheet[0].index("Phone")
        else:
            columnsMissing = True

        if ("Email" in sheet[0]):
            columns["email"] = sheet[0].index("Email")
        else:
            columnsMissing = True

        if ("Company" in sheet[0]):
            columns["company"] = sheet[0].index("Company")
        else:
            columnsMissing = True

        if ("Street Address" in sheet[0]):
            columns["streetAddress"] = sheet[0].index("Street Address")
        else:
            columnsMissing = True

        if ("City" in sheet[0]):
            columns["city"] = sheet[0].index("City")
        else:
            columnsMissing = True

        if ("State/Region" in sheet[0]):
            columns["state"] = sheet[0].index("State/Region")
        else:
            columnsMissing = True

        if ("Country Code" in sheet[0]):
            columns["country"] = sheet[0].index("Country Code")
        else:
            columnsMissing = True

        if ("Postal Code" in sheet[0]):
            columns["postalCode"] = sheet[0].index("Postal Code")
        else:
            columnsMissing = True

        if ("Pricelist" in sheet[0]):
            columns["pricelist"] = sheet[0].index("Pricelist")
        else:
            columnsMissing = True

        if ("Language" in sheet[0]):
            columns["language"] = sheet[0].index("Language")
        else:
            columnsMissing = True

        if ("OCID" in sheet[0]):
            columns["id"] = sheet[0].index("OCID")
        else:
            columnsMissing = True

        if ("Valid" in sheet[0]):
            columns["valid"] = sheet[0].index("Valid")
        else:
            columnsMissing = True

        if ("Continue" in sheet[0]):
            columns["continue"] = sheet[0].index("Continue")
        else:
            columnsMissing = True

        i = 1
        if (len(sheet[i]) != sheetWidth or columnsMissing):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            _logger.info("Sheet Width: " + str(len(sheet[i])))
            return True, msg
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while (True):

            if (i == len(sheet) or str(sheet[i][columns["continue"]]) != "TRUE"):
                break

            if (str(sheet[i][columns["valid"]]) != "TRUE"):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            if (not self.check_id(str(sheet[i][columns["id"]]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            if (not self.check_id(str(sheet[i][columns["company"]]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue
            try:
                external_id = str(sheet[i][columns["id"]])

                contact_ids = self.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'res.partner')])
                if (len(contact_ids) > 0):
                    self.updateContacts(self.env['res.partner'].browse(
                        contact_ids[len(contact_ids) - 1].res_id), sheet, sheetWidth, i, columns)
                else:
                    self.createContacts(sheet, external_id,
                                        sheetWidth, i, columns)
            except Exception as e:
                _logger.info("Contacts")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i += 1
        msg = self.endTable(msg)
        return False, msg

    # follows same pattern
    def updateContacts(self, contact, sheet, sheetWidth, i, columns):

        if (contact.stringRep == str(sheet[i][:])):
            return

        contact.name = sheet[i][columns["name"]]
        contact.phone = sheet[i][columns["phone"]]
        contact.email = sheet[i][columns["email"]]
        if (sheet[i][columns["company"]] != ""):
            contact.parent_id = int(self.env['ir.model.data'].search(
                [('name', '=', sheet[i][columns["company"]]), ('model', '=', 'res.partner')])[0].res_id)
        contact.street = sheet[i][columns["streetAddress"]]
        contact.city = sheet[i][columns["city"]]
        if (sheet[i][columns["state"]] != ""):
            stateTup = self.env['res.country.state'].search(
                [('code', '=', sheet[i][columns["state"]])])
            if (len(stateTup) > 0):
                contact.state_id = int(stateTup[0].id)

        name = sheet[i][columns["country"]]
        if (name != ""):
            if (name == "US"):
                name = "United States"
            contact.country_id = int(
                self.env['res.country'].search([('name', '=', name)])[0].id)
        contact.zip = sheet[i][columns["postalCode"]]

        contact.lang = sheet[i][columns["language"]]

        if (sheet[i][columns["pricelist"]] != ""):
            contact.property_product_pricelist = int(self.env['product.pricelist'].search(
                [('name', '=', sheet[i][columns["pricelist"]])])[0].id)
        contact.is_company = False

        _logger.info("Contact String Rep")
        contact.stringRep = str(sheet[i][:])

    # follows same pattern
    def createContacts(self, sheet, external_id, sheetWidth, i, columns):
        ext = self.env['ir.model.data'].create(
            {'name': external_id, 'model': "res.partner"})[0]
        contact = self.env['res.partner'].create(
            {'name': sheet[i][columns["name"]]})[0]
        ext.res_id = contact.id
        self.updateContacts(contact, sheet, sheetWidth, i, columns)

    # follows same pattern
    def syncProducts(self, sheet):

        sheetWidth = 8
        i = 1

        columns = dict()
        columnsMissing = False

        if ("SKU" in sheet[0]):
            columns["sku"] = sheet[0].index("SKU")
        else:
            columnsMissing = True

        if ("Name" in sheet[0]):
            columns["name"] = sheet[0].index("Name")
        else:
            columnsMissing = True

        if ("Description" in sheet[0]):
            columns["description"] = sheet[0].index("Description")
        else:
            columnsMissing = True

        if ("Price CAD" in sheet[0]):
            columns["priceCAD"] = sheet[0].index("Price CAD")
        else:
            columnsMissing = True

        if ("Price USD" in sheet[0]):
            columns["priceUSD"] = sheet[0].index("Price USD")
        else:
            columnsMissing = True

        if ("Product Type" in sheet[0]):
            columns["type"] = sheet[0].index("Product Type")
        else:
            columnsMissing = True

        if ("Tracking" in sheet[0]):
            columns["tracking"] = sheet[0].index("Tracking")
        else:
            columnsMissing = True

        if ("Valid" in sheet[0]):
            columns["valid"] = sheet[0].index("Valid")
        else:
            columnsMissing = True

        if (len(sheet[i]) != sheetWidth or columnsMissing):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            _logger.info("Sheet Width: " + str(len(sheet[i])))
            return True, msg

        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while (True):
            if (i == len(sheet) or str(sheet[i][columns["valid"]]) != "TRUE"):
                break

            if (not self.check_id(str(sheet[i][columns["sku"]]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            if (not self.check_price(sheet[i][columns["priceCAD"]])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            if (not self.check_price(sheet[i][columns["priceUSD"]])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            try:
                _logger.info("try1")
                external_id = str(sheet[i][columns["sku"]])
                _logger.info("sku: " + external_id)

                _logger.info("try2")
                product_ids = self.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'product.template')])
                _logger.info("product_ids: " + str(product_ids))

                if (len(product_ids) > 0):
                    _logger.info("try3")
                    self.updateProducts(self.env['product.template'].browse(
                        product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i, columns)
                else:
                    _logger.info("try4")
                    self.createProducts(sheet, external_id,
                                        sheetWidth, i, columns)

                    _logger.info("End try")
            except Exception as e:
                _logger.info("Products Exception")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i += 1
        msg = self.endTable(msg)
        return False, msg

    def pricelist(self, product, priceName, pricelistName, i, columns):
        _logger.info("sync pricelist enter")                        
        pricelist_id = self.env['product.pricelist'].search([('name', '=', pricelistName)])[0].id

        _logger.info("sync pricelist Step 1") 
        pricelist_item_ids = self.env['product.pricelist.item'].search(
            [('product_tmpl_id', '=', product.id), ('pricelist_id', '=', pricelist_id)])

        _logger.info("sync pricelist Step 2") 
        if (len(pricelist_item_ids) > 0):

            _logger.info("sync pricelist Step 2.1") 
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            
            _logger.info("sync pricelist Step 2.1.1a")
            _logger.info("product.id: " + str(product.id))

            _logger.info("sync pricelist Step 2.1.1b")
            pricelist_item.product_tmpl_id = product.id

            _logger.info("sync pricelist Step 2.1.2")
            pricelist_item.applied_on = "1_product"

            _logger.info("sync pricelist Step 2.1.3")
            if (str(self.sheet[i][columns[priceName]]) != " " and str(self.sheet[i][columns[priceName]]) != ""):

                _logger.info("sync pricelist Step 2.1.3.1")
                pricelist_item.fixed_price = float(self.sheet[i][columns[priceName]])
        else:
            _logger.info("sync pricelist Step 2.2") 
            pricelist_item = self.env['product.pricelist.item'].create(
                {'pricelist_id': pricelist_id, 'product_tmpl_id': product.id})[0]
            
            _logger.info("sync pricelist Step 2.2.1")             
            pricelist_item.applied_on = "1_product"

            _logger.info("sync pricelist Step 2.2.2") 
            if (str(self.sheet[i][columns[priceName]]) != " " and str(self.sheet[i][columns[priceName]]) != ""):

                _logger.info("sync pricelist Step 2.2.2.1") 
                pricelist_item.fixed_price = self.sheet[i][columns[priceName]]

                _logger.info("sync pricelist Step 2.2.2.2") 

        _logger.info("sync pricelist END")

    # follows same pattern
    def updateProducts(self, product, sheet, sheetWidth, i, columns):

        if (product.stringRep == str(sheet[i][:])):
            return

        product.name = sheet[i][columns["name"]]
        product.description_sale = sheet[i][columns["description"]]
        product.price = sheet[i][columns["priceCAD"]]    
        
        self.pricelist(product,"priceCAD", "CAN Pricelist", i, columns)
        self.pricelist(product, "priceUSD", "USD Pricelist", i, columns)

        #product.cadVal = sheet[i][columns["priceCAD"]]
        #product.usdVal = sheet[i][columns["priceUSD"]]
        product.tracking = "serial"
        product.type = "product"

        _logger.info("Product String Rep")
        product.stringRep = str(sheet[i][:])

    # follows same pattern
    def createProducts(self, sheet, external_id, sheetWidth, i, columns):
        ext = self.env['ir.model.data'].create(
            {'name': external_id, 'model': "product.template"})[0]
        product = self.env['product.template'].create(
            {'name': sheet[i][columns["name"]]})[0]
        ext.res_id = product.id
        _logger.info("str(product.id)")
        _logger.info(str(product.id))
        self.updateProducts(product, sheet, sheetWidth, i, columns)

    

    def syncWebCode(self, sheet):
        # check sheet width to filter out invalid sheets
        # every company tab will have the same amount of columns (Same with others)
        sheetWidth = 8
        columns = dict()
        missingColumn = False

        # Calculate Indexes
        if ("Page ID" in sheet[0]):
            columns["id"] = sheet[0].index("Page ID")
        else:
            missingColumn = True

        if ("HTML" in sheet[0]):
            columns["html"] = sheet[0].index("HTML")
        else:
            missingColumn = True

        if ("Valid" in sheet[0]):
            columns["valid"] = sheet[0].index("Valid")
        else:
            missingColumn = True

        if ("Continue" in sheet[0]):
            columns["continue"] = sheet[0].index("Continue")
        else:
            missingColumn = True

        if (len(sheet[0]) != sheetWidth or missingColumn):
            msg = "<h1>Pricelist page Invalid</h1>\n<p>Sheet width is: " + \
                str(len(sheet[0])) + "</p>"
            self.sendSyncReport(msg)
            _logger.info("Sheet Width: " + str(len(sheet[0])))
            return True, msg

        i = 1
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while (True):
            _logger.info("Website: " + str(i))
            if (i == len(sheet) or str(sheet[i][columns["continue"]]) != "TRUE"):
                break

            if (not self.check_id(str(sheet[i][columns["id"]]))):
                _logger.info("id")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue

            if (not sheet[i][columns["valid"]] == "TRUE"):
                _logger.info("Web Valid")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue

            try:
                _logger.info(sheet[i][columns["id"]])
                external_id = str(sheet[i][columns["id"]])
                # _logger.info(external_id)
                pageIds = self.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'ir.ui.view')])
                # _logger.info(pageIds)
                if (len(pageIds) > 0):
                    page = self.env['ir.ui.view'].browse(pageIds[-1].res_id)
                    opener = "<?xml version=\"1.0\"?>\n<data>\n<xpath expr=\"//div[@id=&quot;wrap&quot;]\" position=\"inside\">\n"
                    closer = "<t t-call=\"custom.custom-footer\"/>\n</xpath>\n</data>"
                    page.arch_base = opener + \
                        sheet[i][columns["html"]] + closer
                else:
                    # msg = self.buildMSG(msg, sheet, sheetWidth, i)
                    msg = "</p>" + str(external_id) + \
                        " Page Not Created</p><br/>\n"
                    _logger.info(str(pageIds))
                    _logger.info(str(external_id) + " Page Not Created")
                i = i + 1
            except Exception as e:
                _logger.info(sheet[i][columns['id']])
                _logger.info(e)
                # msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = ""
                return True, msg
        return False, msg

    def check_id(self, id):
        if (" " in id):
            _logger.info("ID: " + str(id))
            return False
        else:
            return True

    def check_price(self, price):
        if (price in ("", " ")):
            return True
        try:
            float(price)
            return True
        except Exception as e:
            _logger.info(e)
            return False

    def buildMSG(self, msg, sheet, sheetWidth, i):
        if (msg == ""):
            msg = self.startTable(msg, sheet, sheetWidth, True)
        msg = msg + "<tr>"
        j = 0
        while (j < sheetWidth):
            msg = msg + "<td>" + str(sheet[i][j])
            j = j + 1
        msg = msg + "</tr>"
        return msg

    def startTable(self, msg, sheet, sheetWidth, force=False):
        if (force):
            msg = msg + "<table><tr>"
            j = 0
            while (j < sheetWidth):
                msg = msg + "<th><strong>" + \
                    str(sheet[0][j]) + "</strong></th>"
                j = j + 1
            msg = msg + "</tr>"
        elif (msg != ""):
            msg = msg + "<table><tr>"
            while (j < sheetWidth):
                msg = msg + "<th>" + str(sheet[0][j]) + "</th>"
                j = j + 1
            msg = msg + "</tr>"

        return msg

    def endTable(self, msg):
        if (msg != ""):
            msg = msg + "</table>"
        return msg

    def syncCancel(self, msg):
        link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
        msg = "<h1>The Sync Process Was forced to quit and no records were updated</h1><h1> The Following Rows of The Google Sheet Table are invalid<h1>" + \
            msg + "<a href=\"" + link + "\">Manual Retry</a>"
        _logger.info(msg)
        self.sendSyncReport(msg)

    def syncFail(self, msg):
        link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
        msg = "<h1>The Following Rows of The Google Sheet Table are invalid and were not Updated to Odoo</h1>" + \
            msg + "<a href=\"" + link + "\">Manual Retry</a>"
        _logger.info(msg)
        self.sendSyncReport(msg)

    def sendSyncReport(self, msg):
        values = {'subject': 'Sync Report'}
        message = self.env['mail.message'].create(values)[0]

        values = {'mail_message_id': message.id}

        email = self.env['mail.mail'].create(values)[0]
        email.body_html = msg
        email.email_to = "sync@store.r-e-a-l.it"
        email_id = {email.id}
        email.process_email_queue(email_id)
