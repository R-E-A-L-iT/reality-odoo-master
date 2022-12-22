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

    _sync_cancel_reason = "<h1>The Sync Process Was forced to quit and no records were updated</h1><h1> The Following Rows of The Google Sheet Table are invalid<h1>"
    _sync_fail_reason = "<h1>The Following Rows of The Google Sheet Table are invalid and were not Updated to Odoo</h1>"

    _odoo_sync_data_index = 0

    # STARTING POINT
    def start_sync(self, psw=None):
        _logger.info("Starting Sync")

        template_id = self._master_database_template_id       

        sheetName = ""
        sheetIndex = -1
        modelType = ""
        valid = False

        line_index = 1
        msg = ""

        # Checks authentication values
        if (not self.is_psw_format_good(psw)):
            return

        # Get the ODOO_SYNC_DATA tab
        sync_data = self.getMasterDatabaseSheet(template_id, psw, self._odoo_sync_data_index)   

        # loop through entries in first sheet
        while (True):
            msg_temp = ""
            sheetName = str(sync_data[line_index][0])
            sheetIndex, msg_temp = self.getSheetIndex(sync_data, line_index)
            msg += msg_temp
            modelType = str(sync_data[line_index][2])
            valid = (str(sync_data[line_index][3]).upper() == "TRUE")

            if (not valid):
                _logger.info("Valid: " + sheetName + " is " + str(valid) + " because the str was : " + str(sync_data[line_index][3]) + ".  Ending sync process!")
                break

            if (sheetIndex < 0):
                break
            
            _logger.info("Valid: " + sheetName + " is " + str(valid) + ".")
            quit, msgr = self.getSyncValues(sheetName,
                                            psw,
                                            template_id,
                                            sheetIndex,
                                            modelType)
            msg = msg + msgr
            line_index += 1

            if (quit):
                self.syncFail(msg, self._sync_cancel_reason)
                return

        # error
        if (msg != ""):
            self.syncFail(msg, self._sync_fail_reason)

        _logger.info("Ending Sync")

    #Check the password format
    #Input
    #   psw:   The password to open the googlesheet
    #Output
    #   True : Password format is good
    #   False: Password format if bad
    def is_psw_format_good(self, psw):  

        # Checks authentication values
        if ((psw == None) or (str(type(psw)) != "<class 'dict'>")):
            msg = "<h1>Sync Error</h1><p>Authentication values Missing</p>"
            _logger.info(msg)
            self.sendSyncReport(msg)
            return False
        
        return True


    #Get a tab in the GoogleSheet Master Database
    #Input
    #   template_id:    The GoogleSheet Template ID to acces the master database
    #   psw:            The password to acces the DB
    #   index:          The index of the tab to pull
    #Output
    #   data:           A tab in the GoogleSheet Master Database
    def getMasterDatabaseSheet(self, template_id, psw, index):  
        # get the database data; reading in the sheet
        
        try:
            return (self.getDoc(psw, template_id, index))
        except Exception as e:
            _logger.info(e)
            msg = "<h1>Source Document Invalid</h1><p>Sync Fail</p>"
            self.syncFail(msg, self._sync_fail_reason)            
            quit

    #Get the Sheet Index of the Odoo Sync Data tab, column B
    # Input
    #   sync_data:  The GS ODOO_SYNC_DATA tab
    #   lineIndex:  The index of the line to get the SheetIndex
    # Output
    #   sheetIndex: The Sheet Index for a given Abc_ODOO tab to read
    #   msg:        Message to append to the repport
    def getSheetIndex(self, sync_data, lineIndex):
        sheetIndex = -1
        i = -1        
        msg = ""

        if (lineIndex < 1):
            return -1

        i = self.getColumnIndex(sync_data, "Sheet Index")
        if (i < 0):
            return -1            

        try:
            sheetIndex = int(sync_data[lineIndex][i])
        except ValueError:
            sheetIndex = -1
            msg = "BREAK: check the tab ODOO_SYNC_DATA, there must have a non numeric value in column number " + \
                str(i) + "called 'Sheet Index', line " + str(lineIndex) + ": " + str(sync_data[lineIndex][1]) + "."
            _logger.info(msg)
        
        return sheetIndex, msg

    #Method to get the sync_pricelist calss.
    #Input
    #   sheetName: The name of the tab
    #   sheet:     The sheet in format 
    #      [['ColumnName1','ColumnName2',...,'ColumnNameX'],
    #       ['Line1 Column1','Line1 Column2',...,'Line1 ColumnX'],
    #       ['Line2 Column1','Line2 Column2',...,'Line2 ColumnX'],
    #       ...,
    #       ['LineZ Column1','LineZ Column2',...,'LineZ ColumnX']]
    #Output
    #   An instance of sync_pricelist
    def getSync_pricelist(self, sheetName, sheet):
        return sync_pricelist(sheetName, sheet, self)

    def getSyncValues(self, sheetName, psw, template_id, sheetIndex, syncType):

        sheet = self.getMasterDatabaseSheet(template_id, psw, sheetIndex)

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
            syncer = self.getSync_pricelist(sheetName, sheet)
            quit, msg = syncer.syncPricelist()
            quit = False
            msg = ""
            # quit, msg = self.syncPricelist(sheet)

        elif (syncType == "WebHTML"):
            quit, msg = self.syncWebCode(sheet)

        _logger.info("Done with " + syncType)

        if (quit):
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
            if (str(sheet[i][columns["continue"]]).upper() != "TRUE"):
                break

            # validation checks (vary depending on tab/function)
            if (str(sheet[i][columns["valid"]]).upper() != "TRUE"):
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

            if (i == len(sheet) or str(sheet[i][columns["continue"]]).upper() != "TRUE"):
                break

            if (str(sheet[i][columns["valid"]]).upper() != "TRUE"):
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
        msg = self.startTable(msg, sheet, sheetWidth)
        while (True):
            

            _logger.info("sheet[i][:]: " + str(sheet[i][:]))

            if (str(sheet[i][columns["continue"]]).upper() != "TRUE"):
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
                external_id = str(sheet[i][columns["sku"]])
                product_ids = self.env['ir.model.data'].search(
                    [('name', '=', external_id), ('model', '=', 'product.template')])

                if (len(product_ids) > 0):
                    product=self.env['product.template'].browse(
                        product_ids[len(product_ids) - 1].res_id)
                    self.updateProducts(
                        product, 
                        str(sheet[i][:]),                   #product_stringRep
                        sheet[i][columns["name"]],          #product_name
                        sheet[i][columns["description"]],   #product_description_sale
                        sheet[i][columns["priceCAD"]],      #product_price_cad
                        sheet[i][columns["priceUSD"]],      #product_price_usd
                        "serial",                           #product_tracking
                        "product")                          #product_type
                else:
                    self.createAndUpdateProducts(
                        external_id, 
                        str(sheet[i][:]),                   #product_stringRep
                        sheet[i][columns["name"]],          #product_name
                        sheet[i][columns["description"]],   #product_description_sale
                        sheet[i][columns["priceCAD"]],      #product_price_cad
                        sheet[i][columns["priceUSD"]],      #product_price_usd
                        "serial",                           #product_tracking
                        "product")                          #product_type

            except Exception as e:
                _logger.info("Products Exception")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg

            i += 1

        msg = self.endTable(msg)
        return False, msg

    #Method to create a product
    #Input
    #   external_id:    The external id, wich is the SKU key in the GoogleSheet Database.  
    #   product_name:   Name of the product
    #Output             
    #   product:        The product generated by Odoo
    def createProducts(self, external_id, product_name):
        product = None
        ext = self.env['ir.model.data'].create(
            {'name': external_id, 'model': "product.template"})[0]
        product = self.env['product.template'].create(
            {'name': product_name})[0]
        
        product.tracking = "serial"
        product.type = "product"
        ext.res_id = product.id

        return product

    #Methode to update product information.
    #Input
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

        # pricelist need to be done before modifiyng the product.price
        # since it will be erased be the addProductToPricelist.  Apparently,
        # Odoo set to price to 0 if we set the product in a pricelist.
        syncer = sync_pricelist("", [], self)
        syncer.addProductToPricelist(product, "CAN Pricelist", product_price_cad)
        syncer.addProductToPricelist(product, "USD Pricelist", product_price_usd) 

        product.name                = product_name
        product.description_sale    = product_description_sale        
        product.price               = product_price_cad 
        product.tracking            = product_tracking
        product.type                = product_type
        product.stringRep           = product_stringRep

    #Method to create and update a product
    #Input
    #   external_id:                The SKU in GoogleSheet
    #   product_stringRep:          The GoogleSheet line that represent all the informations of the product
    #   product_name:               Product Name
    #   product_description_sale:   English dercription
    #   product_price_cad:          Price in CAD
    #   product_price_usd:          Price in USD
    #   product_tracking:           Tracking
    #   product_type:               Type
    #Output
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

        product_created = self.env['product.template'].search(
            [('sku', '=', external_id)]) 
        return product_created    

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
            if (i == len(sheet) or str(sheet[i][columns["continue"]]).upper() != "TRUE"):
                break

            if (not self.check_id(str(sheet[i][columns["id"]]))):
                _logger.info("id")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
                continue

            if (not sheet[i][columns["valid"]].upper() == "TRUE"):
                _logger.info("Web Valid")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i += 1
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
                i += 1
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
            j += 1
        msg = msg + "</tr>"
        return msg

    def startTable(self, msg, sheet, sheetWidth, force=False):
        if (force):
            msg = msg + "<table><tr>"
            j = 0
            while (j < sheetWidth):
                msg = msg + "<th><strong>" + \
                    str(sheet[0][j]) + "</strong></th>"
                j += 1
            msg = msg + "</tr>"
        elif (msg != ""):
            msg = msg + "<table><tr>"
            while (j < sheetWidth):
                msg = msg + "<th>" + str(sheet[0][j]) + "</th>"
                j += 1
            msg = msg + "</tr>"

        return msg

    def endTable(self, msg):
        if (msg != ""):
            msg = msg + "</table>"
        return msg

    #Build the message when a sync fail occurs.  Once builded, it will display the message
    #in the logger, and send a repport by email.
    #Input
    #   msg:    The msg that contain information on the failling issue
    #   reason: The reason that lead to the faillur.
    def syncFail(self, msg, reason):
        link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
        msg = reason + \
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

    def archive_product(self, product_id):
        product = self.env['product.template'].search([('id', '=', product_id)])
        product.active = False

    def getListSkuGS(self, psw, template_id):
        _logger.info("------------------------------------------- Starting getListSkuGS")               
        catalog_gs = dict()

        sheetName = ""
        sheetIndex = -1
        modelType = ""
        valid = False

        i = 1
        msg = ""        

        # Get the ODOO_SYNC_DATA tab
        sync_data = self.getOdooSyncData(template_id, psw, self._odoo_sync_data_index)

        # loop through entries in first sheet
        while (True):
            msg_temp = ""
            sheetName = str(sync_data[i][0])
            sheetIndex, msg_temp = self.getSheetIndex(sync_data, i)
            msg += msg_temp
            modelType = str(sync_data[i][2])
            valid = (str(sync_data[i][3]).upper() == "TRUE")            

            if (not valid):
                _logger.info("Valid: " + sheetName + " is " + str(valid) + ".  Ending Sku Cleaning process!")
                break

            if (sheetIndex < 0):
                break         

            sheet = self.getMasterDatabaseSheet(template_id, psw, sheetIndex)
            validColumnIndex = self.getColumnIndex(sheet, "Valid")
            skuColumnIndex  = self.getColumnIndex(sheet, "SKU")

            if (validColumnIndex < 0):
                _logger.info("Sheet: " + sheetName + " does not have a Valid column.")
                continue

            if ((modelType == "Pricelist") or (modelType == "CCP")):
                lineIndex = 0
                for line in sheet:
                    line_valid = (str(line[validColumnIndex]).upper() == "TRUE")
                    sku = str(line[skuColumnIndex])

                    #Validation on the line
                    if(not line_valid):
                        break

                    if (sku == "False" or sku == ""):
                        _logger.info("An item SKU is empty in the tab " +  sheetName + ", line number " + str(lineIndex))
                        continue
                    
                    if (sku not in catalog_gs):
                        catalog_gs[sku] = 1
                    else:
                        catalog_gs[sku] = catalog_gs[sku] + 1
                    
                    lineIndex += 1
            
            i += 1               

        return catalog_gs

    #Return the column index of the columnName
    #Input
    #   sheet:      The sheet to find the Valid column index
    #   columnName: The name of the column to find
    #Output
    #   columnIndex: -1 if could not find it
    #                > 0 if a column name exist
    def getColumnIndex (self, sheet, columnName):
        header = sheet[0]
        columnIndex = 0

        for column in header:
            if (column == columnName):
                return columnIndex
            
            columnIndex += 1
        
        return -1


    #Sku cleaning
    def start_sku_cleaning(self, psw=None):
        _logger.info("------------------------------------------- BEGIN start_sku_cleaning")

        catalog_odoo = dict()
        catalog_gs = dict()
        to_archives = []

        # Checks authentication values
        if (not self.is_psw_format_good(psw)):
            _logger.info("------------------------------------------- END start_sku_cleaning: psw is empty")
            return

        #################################
        # Odoo Section        
        products = self.env['product.template'].search([])
        _logger.info("products length befor clean up: " + str(len(products)))
        
        for product in products:            
            if (product.active == False):               
                continue

            if ((str(product.sku) == "False") or (str(product.sku) == None)):
                to_archives.append(str(product.id))
                _logger.info("------------------------------------------- To archives: product id: " + str(product.id) + ", active is: " + str(product.active) + ", name: " + str(product.name))

            if (str(product.sku) not in catalog_odoo):
                catalog_odoo[str(product.sku)] = 1
            else:
                catalog_odoo[str(product.sku)] = catalog_odoo[str(product.sku)] + 1

        _logger.info("catalog_odoo length: " + str(len(catalog_odoo)))

        #######################################
        # GoogleSheet Section        
        catalog_gs = self.getListSkuGS(psw, self._master_database_template_id)



        for item in to_archives:
            self.archive_product(str(item))
        
        _logger.info("------------------------------------------- END start_sku_cleaning")    
