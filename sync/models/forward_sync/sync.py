#  -*- coding: utf-8 -*-

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
from .company import sync_companies
from .contact import sync_contacts
from .cleaningData import cleanSyncData

_logger = logging.getLogger(__name__)


class sync(models.Model):
    _name = "sync.sync"
    _inherit = "sync.sheets"
    DatabaseURL = fields.Char(default="")
    _description = "Sync App"

    _sync_cancel_reason = "<h1>The Sync Process Was forced to quit and no records were updated</h1><h1> The Following Rows of The Google Sheet Table are invalid<h1>"
    _sync_fail_reason = "<h1>The Following Rows of The Google Sheet Table are invalid and were not Updated to Odoo</h1>"

    _odoo_sync_data_index = 0

    
    def __init__(self, pool, cr):
        super(sync, self).__init__(pool, cr)
        self.cleanSync = cleanSyncData(self)

    @property
    def cleanSync(self):
        return self._clean_sync
    
    @cleanSync.setter
    def cleanSync(self, value):
        self._clean_sync = value        


    ###################################################################
    # STARTING POINT
    def start_sync(self, psw=None):
        _logger.info("Starting Sync")
        db_name = self.env['ir.config_parameter'].sudo(
        ).get_param('web.base.url')
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


    ###################################################################
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


    ###################################################################
    def getSyncValues(self, sheetName, psw, template_id, sheetIndex, syncType):

        sheet = self.getMasterDatabaseSheet(template_id, psw, sheetIndex)

        _logger.info("Sync Type is: " + syncType)
        # identify the type of sheet
        if (syncType == "Companies"):
            syncer = sync_companies(sheetName, sheet, self)
            quit, msg = syncer.syncCompanies()

        elif (syncType == "Contacts"):
            syncer = sync_contacts(sheetName, sheet, self)
            quit, msg = syncer.syncContacts()

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


    ###################################################################
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


    ###################################################################
    def sendSyncReport(self, msg):
        values = {'subject': 'Sync Report'}
        message = self.env['mail.message'].create(values)[0]

        values = {'mail_message_id': message.id}

        email = self.env['mail.mail'].create(values)[0]
        email.body_html = msg
        email.email_to = "sync@store.r-e-a-l.it"
        email_id = {email.id}
        email.process_email_queue(email_id)


    ###################################################################
    # Method to manualy correct on company
    # Input
    #       p_OwnerID: The short name of the contacted added in GS.  Ex "DIGITALPRECISIO"
    #       p_Name: The name of the contact in Odoo.  Ex "Digital Precision Metrology Inc"
    # Error
    #       Raise an error if contact name does not exist
    def addContact(self, p_OwnerID, p_Name):
        _logger.info("addContact: " + str(p_OwnerID) + ", " + str(p_Name))

        #Check if contact name exist 
        company = self.env["res.partner"].search([("name", "=", str(p_Name))])
        if (len(company) > 0):
            company = company[0]
        else:
             raise Exception("Contact name does not exist")

        #Check if OwnerID exist
        ownersID = self.env["ir.model.data"].search([("name", "=",str(p_OwnerID))])
        if (len(ownersID) > 0):
            ext = ownersID[0]
        else:
            ext = self.env["ir.model.data"].create({"name":str(p_OwnerID), "model":"res.partner"})[0]  
        
        #Assigning the company id
        ext.res_id = company.id
        _logger.info("-------------Contact added.")
        


    # ###################################################################
    # # Method to clean all sku that are pulled on the GoogleSheet DB
    # def cleanSku(self, psw=None, p_archive=False, p_optNoSku=True, p_optInOdooNotGs=True):
    #     cleanner = cleanSyncData(self)
    #     cleanner.cleanSku(psw, p_archive, p_optNoSku, p_optInOdooNotGs)


    # ###################################################################
    # #
    # def cleanProductByName(self):
    #     cleanner = cleanSyncData(self)
    #     cleanner.cleanProductByName()


    # ###################################################################
    # #Clean unsued CCP
    # def cleanCCPUnsed(self, p_eid_list, p_ccp_sku_list):
    #     cleanner = cleanSyncData(self)
    #     cleanner.cleanCCPUnsed(p_eid_list, p_ccp_sku_list)


    # ###################################################################
    # #Delete all the unsued SPL
    # def cleanSPLUnsed(self):
    #     cleanner = cleanSyncData(self)
    #     cleanner.cleanSPLUnsed()


    # ###################################################################
    # #Migrate CCP Sku
    # def migrateCCP(self, ccpSkus):
    #     cleanner = cleanSyncData(self)
    #     cleanner.migrateCCP(ccpSkus)


    # ###################################################################
    # #Delete ir.model.data key that are invalide
    # def cleanIMD(self, ccpSkus):
    #     cleanner = cleanSyncData(self)
    #     cleanner.cleanIMD(ccpSkus)


    # ###################################################################
    # #Clean SPL with no owner
    # def cleanSPLNoOwner(self):
    #     cleanner = cleanSyncData(self)
    #     cleanner.cleanSPLNoOwner()
        

