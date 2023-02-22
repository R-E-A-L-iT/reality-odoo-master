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
from .googlesheetsAPI import sheetsAPI
from .website import syncWeb
from .product import sync_products

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
        db_name = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        template_id = sheetsAPI.get_master_database_template_id(db_name)
        _logger.info("db_name: " + str(db_name))
        _logger.info("template_id: " + str(template_id))
        
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
        sync_data = self.getMasterDatabaseSheet(
            template_id, psw, self._odoo_sync_data_index)

        # loop through entries in first sheet
        while (True):
            msg_temp = ""
            sheetName = str(sync_data[line_index][0])
            sheetIndex, msg_temp = self.getSheetIndex(sync_data, line_index)
            msg += msg_temp
            modelType = str(sync_data[line_index][2])
            valid = (str(sync_data[line_index][3]).upper() == "TRUE")

            if (not valid):
                _logger.info("Valid: " + sheetName + " is " + str(valid) + " because the str was : " +
                             str(sync_data[line_index][3]) + ".  Ending sync process!")
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

    # Check the password format
    # Input
    #   psw:   The password to open the googlesheet
    # Output
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

    # Get a tab in the GoogleSheet Master Database
    # Input
    #   template_id:    The GoogleSheet Template ID to acces the master database
    #   psw:            The password to acces the DB
    #   index:          The index of the tab to pull
    # Output
    #   data:           A tab in the GoogleSheet Master Database

    def getMasterDatabaseSheet(self, template_id, psw, index):
        # get the database data; reading in the sheet

        try:
            return (self.getDoc(psw, template_id, index))
        except Exception as e:
            _logger.info(e)
            msg = "<h1>Failed To Retrieve Master Database Document</h1><p>Sync Fail</p><p>" + \
                str(e) + "</p>"
            self.syncFail(msg, self._sync_fail_reason)
            quit

    # Get the Sheet Index of the Odoo Sync Data tab, column B
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
                str(i) + " called 'Sheet Index', line " + \
                str(lineIndex) + ": " + str(sync_data[lineIndex][1]) + "."
            _logger.info(sync_data)

            _logger.info(msg)
            # test to push

        return sheetIndex, msg

    def getSyncValues(self, sheetName, psw, template_id, sheetIndex, syncType):

        sheet = self.getMasterDatabaseSheet(template_id, psw, sheetIndex)

        _logger.info("Sync Type is: " + syncType)
        # identify the type of sheet
        if (syncType == "Companies"):
            quit, msg = self.syncCompanies(sheet)

        elif (syncType == "Contacts"):
            quit, msg = self.syncContacts(sheet)

        elif (syncType == "Products"):
            syncer = sync_products(sheetName, sheet, self)
            quit, msg = syncer.syncProducts(sheet)

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
            syncer = syncWeb(sheetName, sheet, self)
            quit, msg = syncer.syncWebCode(sheet)
            if msg != "":
                _logger.error(msg)

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

    # Build the message when a sync fail occurs.  Once builded, it will display the message
    # in the logger, and send a repport by email.
    # Input
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
        product = self.env['product.template'].search(
            [('id', '=', product_id)])
        product.active = False

    # Get all value in column of a sheet.  If column does not exist, it will return an empty dict().
    # IMPORTANT:     Row must containt a Valid and Continue column.
    #               Row is skippd if valid is False
    #               Method is exit if the Continue is False
    #
    # Exception
    #   MissingColumnError:  If thrown, the column name is missing.
    #                        If thrown, the column "Valid" is missing.
    #                        If thrown, the column "Continue" is missing.
    # Input
    #   sheet: The sheet to look for all the SKU
    # Output
    #   sku_dict: A dictionnary that contain all the SKU as key, and the value is set to 'SKU'

    def getAllValueFromColumn(self, sheet, column_name):
        sku_dict = dict()
        columnIndex = self.getColumnIndex(sheet, column_name)
        sheet_valid_column_index = self.getColumnIndex(sheet, "Valid")
        sheet_continue_column_index = self.getColumnIndex(sheet, "Continue")

        if (columnIndex < 0):
            raise Exception(
                'MissingColumnError', ("The following column name is missing: " + str(column_name)))

        if (sheet_valid_column_index < 0):
            raise Exception('MissingColumnError',
                            ("The following column name is missing: Valid"))

        if (sheet_continue_column_index < 0):
            raise Exception('MissingColumnError',
                            ("The following column name is missing: Continue"))

        sheet_sku_column_index = self.getColumnIndex(sheet, column_name)

        for i in range(1, len(sheet)):
            if (not str(sheet[i][sheet_continue_column_index]).upper() == "TRUE"):
                break

            if (not str(sheet[i][sheet_valid_column_index]).upper() == "TRUE"):
                continue

            sku_dict[sheet[i][sheet_sku_column_index]] = column_name

        return sku_dict


    # Check if a all key unique in two dictionnary
    # Input
    #   dict_small: the smallest dictionnary
    #   dict_big:   The largest dictionnary
    # Output
    #   1st:    True: There is at least one key that exists in both dictionary
    #           False: All key are unique
    #   2nd:    The name of the duplicated Sku
    def checkIfKeyExistInTwoDict(self, dict_small, dict_big):
        for sku in dict_small.keys():
            if sku in dict_big.keys():
                errorMsg = str(sku)
                _logger.info(
                    "------------------------------------------- errorMsg = str(sku): " + str(sku))
                return True, errorMsg
        return False, ""


    # Method to get the ODOO_SYNC_DATA column index
    # Exception
    #   MissingTabError:  If thrown, there is a missing tab.  Further logic should not execute since the MasterDataBase does not have the right format.
    # Input
    #   odoo_sync_data_sheet:   The ODOO_SYNC_DATA tab pulled
    # Output
    #   result: A dictionnary:  Key: named of the column
    #                           Value: the index number of that column.
    def checkOdooSyncDataTab(self, odoo_sync_data_sheet):
        odoo_sync_data_sheet_name_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Sheet Name")
        odoo_sync_data_sheet_index_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Sheet Index")
        odoo_sync_data_model_type_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Model Type")
        odoo_sync_data_valid_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Valid")
        odoo_sync_data_continue_column_index = self.getColumnIndex(
            odoo_sync_data_sheet, "Continue")

        if (odoo_sync_data_sheet_name_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Sheet Name' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_sheet_index_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Sheet Index' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_model_type_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Model Type' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_valid_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Valid' column.")
            raise Exception('MissingTabError', error_msg)

        if (odoo_sync_data_continue_column_index < 0):
            error_msg = (
                "Sheet: ODOO_SYNC_DATA does not have a 'Continue' column.")
            raise Exception('MissingTabError', error_msg)

        result = dict()

        result['odoo_sync_data_sheet_name_column_index'] = odoo_sync_data_sheet_name_column_index
        result['odoo_sync_data_sheet_index_column_index'] = odoo_sync_data_sheet_index_column_index
        result['odoo_sync_data_model_type_column_index'] = odoo_sync_data_model_type_column_index
        result['odoo_sync_data_valid_column_index'] = odoo_sync_data_valid_column_index
        result['odoo_sync_data_continue_column_index'] = odoo_sync_data_continue_column_index

        return result


    # Get all SKU from the model type 'Products' and 'Pricelist'
    # Exception
    #   MissingSheetError:  A sheet is missing
    #   MissingTabError:    A tab in a sheet is missing
    #   SkuUnicityError:    A SKU is not unique
    # Input
    #   psw:            password to acces the Database
    #   template_id:    GoogleSheet TemplateID
    # Output
    #   sku_catalog_gs: A dictionnary that contain all the SKU as key, and 'SKU as value
    def getListSkuGS(self, psw, template_id):
        sku_catalog_gs = dict()

        i = 0
        msg = ""

        # Get the ODOO_SYNC_DATA tab
        sync_data = self.getMasterDatabaseSheet(
            template_id, psw, self._odoo_sync_data_index)

        # check ODOO_SYNC_DATA tab
        result_dict = self.checkOdooSyncDataTab(sync_data)
        odoo_sync_data_sheet_name_column_index  = result_dict['odoo_sync_data_sheet_name_column_index']
        odoo_sync_data_sheet_index_column_index = result_dict['odoo_sync_data_sheet_index_column_index']
        odoo_sync_data_model_type_column_index  = result_dict['odoo_sync_data_model_type_column_index']
        odoo_sync_data_valid_column_index       = result_dict['odoo_sync_data_valid_column_index']
        odoo_sync_data_continue_column_index    = result_dict['odoo_sync_data_continue_column_index']

        while (i < len(sync_data)):
            i += 1
            sheet_name = ""
            refered_sheet_index = -1
            msg_temp = ""
            modelType = ""
            valid_value = False
            continue_value = False
            sku_dict = dict()
            refered_sheet_valid_column_index = -1
            refered_sheet_sku_column_index = -1

            sheet_name = str    (sync_data[i][odoo_sync_data_sheet_name_column_index])
            refered_sheet_index, msg_temp = self.getSheetIndex(sync_data, i)
            msg += msg_temp
            modelType = str     (sync_data[i][odoo_sync_data_model_type_column_index])
            valid_value =       (str(sync_data[i][odoo_sync_data_valid_column_index]).upper() == "TRUE")
            continue_value =    (str(sync_data[i][odoo_sync_data_continue_column_index]).upper() == "TRUE")

            # Validation for the current loop
            if (not continue_value):
                #_logger.info("------------------------------------------- BREAK not continue_value while i: " + str(i))
                break

            if ((modelType not in ["Pricelist", "Products"])):
                #_logger.info("------------------------------------------- continue (modelType != 'Pricelist') or (modelType != 'Products') while i: " + str(i) + " model: " + str(modelType))
                continue

            if (not valid_value):
                #_logger.info("------------------------------------------- continue (not valid_value) while i: " + str(i))
                continue

            if (refered_sheet_index < 0):
                error_msg = ("Sheet Name: " + sheet_name +
                             " is missing in the GoogleData Master DataBase.  The Sku Cleaning task could not be executed!")
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('MissingSheetError', error_msg)

            # Get the reffered sheet
            refered_sheet = self.getMasterDatabaseSheet(
                template_id, psw, refered_sheet_index)
            refered_sheet_valid_column_index = self.getColumnIndex(
                refered_sheet, "Valid")
            refered_sheet_sku_column_index = self.getColumnIndex(
                refered_sheet, "SKU")

            # Validation
            if (refered_sheet_valid_column_index < 0):
                error_msg = ("Sheet: " + sheet_name +
                             " does not have a 'Valid' column. The Sku Cleaning task could not be executed!")
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('MissingTabError', error_msg)

            if (refered_sheet_sku_column_index < 0):
                error_msg = ("Sheet: " + sheet_name +
                             " does not have a 'SKU' column. The Sku Cleaning task could not be executed!")
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('MissingTabError', error_msg)

            # main purpose
            sku_dict = self.getAllValueFromColumn(refered_sheet, "SKU")
            result, sku_in_double = self.checkIfKeyExistInTwoDict(sku_dict, sku_catalog_gs)

            if (result):
                error_msg = (
                    "The folowing SKU appear twice in the Master Database: " + str(sku_in_double))
                _logger.info(
                    "------------------------------------------- raise while i: " + str(i) + " " + error_msg)
                raise Exception('SkuUnicityError', error_msg)

            for sku in sku_dict:
                sku_catalog_gs[sku] = "sku"

        return sku_catalog_gs

    # Return the column index of the columnName
    # Input
    #   sheet:      The sheet to find the Valid column index
    #   columnName: The name of the column to find
    # Output
    #   columnIndex: -1 if could not find it
    #                > 0 if a column name exist
    def getColumnIndex(self, sheet, columnName):
        header = sheet[0]
        columnIndex = 0

        for column in header:
            if (column == columnName):
                return columnIndex

            columnIndex += 1

        return -1


    # Method the return a list of product.id need to be archived.
    # The list include all product.id that does not have a prodcut.sku, or that the string or product.sku is False.
    # The list include all product.id that the product.sku is in Odoo and not in GoogleSheet Master Database.
    # Input
    #   psw: the password to acces the GoogleSheet Master Database.
    # Output
    #   to_archive: a list of product.id
    def getSkuToArchive(self, psw=None):
        _logger.info(
            "------------------------------------------- BEGIN  to get the sku in odoo and not in GoogleSheet")
        catalog_odoo = dict()
        catalog_gs = dict()
        to_archive = []

        # Checks authentication values
        if (not self.is_psw_format_good(psw)):
            _logger.info("Password not valid")
            return

        #################################
        # Odoo Section
        products = self.env['product.template'].search([])
        _logger.info("products length before clean up: " + str(len(products)))

        for product in products:
            if (product.active == False):
                continue

            if ((str(product.sku) == "False") or (str(product.sku) == None)):
                if (str(product.id) != "False"):
                    to_archive.append(str(product.id))
                else:
                    _logger.info("Odoo section, str(product.id) was False.")

                _logger.info("---------------- To archived: Product with NO SKU: Product id: " + str(product.id).ljust(
                    10) + ", active is: " + str(product.active).ljust(7) + ", name: " + str(product.name))

            if (str(product.sku) not in catalog_odoo):
                catalog_odoo[str(product.sku)] = 1
            else:
                catalog_odoo[str(product.sku)
                             ] = catalog_odoo[str(product.sku)] + 1

        #######################################
        # GoogleSheet Section
        try:
            db_name = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            template_id = sheetsAPI.get_master_database_template_id(db_name)
            catalog_gs = self.getListSkuGS(psw, template_id)

        except Exception as e:
            _logger.info(
                "Cleaning Sku job is interrupted with the following error : \n" + str(e))
            return

        #######################################
        # listing product in Odoo and not in GS
        for item in catalog_odoo:
            if (not item in catalog_gs):
                product = self.env['product.template'].search(
                    [('sku', '=', item)])
                _logger.info("---------------- To archived: In Odoo, NOT in GS: Product id:  " + str(
                    product.id).ljust(10) + "sku: " + str(product.sku).ljust(55) + "name: " + str(product.name))
                if (str(product.id) == "False"):
                    _logger.info(
                        "listing product in Odoo and not in GS, str(product.id) was False.")
                elif (str(product.sku) == "time_product_product_template"):
                    _logger.info("Can not archive Service on Timesheet.")
                else:
                    to_archive.append(str(product.id))

        _logger.info("catalog_gs length: " + str(len(catalog_gs)))
        _logger.info("catalog_odoo length: " + str(len(catalog_odoo)))
        _logger.info("to_archive length: " + str(len(to_archive)))
        return to_archive


    # Method to clean all sku that are pulled by self.getSkuToArchive
    def cleanSku(self, psw=None):
        to_archive_list = self.getSkuToArchive(psw)
        to_archive_dict = dict()
        sales_with_archived_product = 0

        # Archiving all unwanted products
        #_logger.info("------------------------------------------- Number of products to archied: " + str(len(to_archive_list)))
        #archiving_index = 0
        # for item in to_archive_list:
        #    _logger.info(str(archiving_index) + " archving :" + str(item))
        #    archiving_index += 1
        #    self.archive_product(str(item))
        #_logger.info("------------------------------------------- ALL products with no SKU or Sku in Odoo and not in GoogleSheet DB are archived.")

        # Switch to dictionnary to optimise the rest of the querry
        for i in range(len(to_archive_list)):
            to_archive_dict[to_archive_list[i]] = 'sku'

        # Listing all sale.order that contain archhived product.id
        order_object_ids = self.env['sale.order'].search([('id', '>', 0)])
        for order in order_object_ids:
            sale_order_lines = self.env['sale.order.line'].search(
                [('order_id', '=', order.id)])

            for line in sale_order_lines:
                product = self.env['product.product'].search(
                    [('id', '=', line.product_id.id)])
                if (str(product.id) in to_archive_dict):
                    if ((str(product.id) != "False")):
                        _logger.info("---------------")
                        _logger.info("orders name: " + str(order.name))
                        _logger.info("id in a sale order: " + str(product.id))
                        _logger.info("sku in a sale order: " +
                                     str(product.sku))
                        _logger.info("name in a sale order: " +
                                     str(product.name))
                        _logger.info("---------------")
                        sales_with_archived_product += 1

        _logger.info("number of sales with archived product: " +
                     str(sales_with_archived_product))


    # Method to log all product id, sku, skuhidden and name
    # Input
    #   sale_name: the name of the sale order
    def log_product_from_sale(self, sale_name):
        _logger.info("Listing all product from: " + str(sale_name))
        order_object_ids = self.env['sale.order'].search(
            [('name', '=', sale_name)])
        for order in order_object_ids:
            sale_order_lines = self.env['sale.order.line'].search(
                [('order_id', '=', order.id)])

            for line in sale_order_lines:
                product = self.env['product.product'].search(
                    [('id', '=', line.product_id.id)])
                _logger.info("---------------")
                _logger.info("orders name: " + str(order.name))
                _logger.info("id in a sale order: " + str(product.id))
                _logger.info("sku in a sale order: " + str(product.sku))
                _logger.info("skuhidden name in a sale order: " +
                             str(product.skuhidden.name))
                _logger.info("name in a sale order: " + str(product.name))
                _logger.info("---------------")

        _logger.info("Listing all product from: END")


    # query to find the QUOTATION-2023-01-05-007, id 552
    def searchQuotation(self):
        sale = self.env['sale.order'].search(
            [('id', '=', 552)])
        _logger.info("--------------- sale.order.")
        _logger.info("sale.id: " + str(sale.id))
        _logger.info("sale.name: " + str(sale.name))
        _logger.info("---------------")

    
    # Method to identify all product with the same name
    def getProductsWithSameName(self):
        productNamesInDouble = []
        names_identified = dict()
        products = self.env['product.template'].search([])

        _logger.info("------------------------------------------------------------------")
        _logger.info("---------------  getProductsWithSameName")        
        _logger.info("---------------  getProductsWithSameName: Number of product to check: " + str(len(products)))        
       
        #For each product, 
        for product in products:
            if (product.active == False):
                continue

            # Check if the product is already identfied
            if (product.name in names_identified):
                continue            
            names_identified[product.name] = True

            #checking if their is other products with the same name.
            doubled_names = self.env['product.template'].search(
                [('name', '=', product.name)])           

            if (len(doubled_names) > 1):
                id_list = []                
                #if yes, adding all the product id founded and the name in a list
                for doubled_name in doubled_names:
                    _logger.info("--------------- id: " + str(doubled_name.id).ljust(10) + str(product.name))
                    id_list.append(doubled_name.id)

                productNamesInDouble.append((str(product.name), id_list))
        
     #14372   
    def getSaleOrderByProductId(self, product_id):
        sales = self.env['sale.order'].search([])
        _logger.info("--------------- Checking for sales with product id: " + str(product_id))
        for sale in sales:
            lines = self.env['sale.order.line'].search([
                ('order_id', '=', sale.id)])
            
            for line in lines:
                    _logger.info("--------------- line.product_id: " + str(line.product_id ))
                # if (line.product_id == product_id):
                #     _logger.info("--------------- id: " + str(line.product_id ))



    def getProductIdBySku(self, p_sku):
        product = self.env['product.product'].search([
            ('sku', '=', p_sku)])        
        _logger.info("--------------- p_sku: " + str(p_sku) + ", id: " + str(product.id))

            
