# -*- coding: utf-8 -*-
import gspread

from odoo import api, fields, models
from odoo.exceptions import UserError
from oauth2client.service_account import ServiceAccountCredentials as sac

import logging

_logger = logging.getLogger(__name__)
# Prefixes Used in Branches To Differentiate Branches
dev_oli = "dev-oli-"
dev_zek = "dev-zek-"
dev_braincrew = "dev-bc-"



class sheetsAPI(models.Model):
    _name = "sync.sheets"
    _inherit = "google.drive.config"
    _description = "Google Sheets API Handler"

    # Method that return the GoogleSheet Master DataBase TemplateID based on the DEV/PROD environnement
    # Input
    #   _db_name : The DB name of the environement that require the template ID
    #              to get it: self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    @staticmethod
    def get_master_database_template_id(_db_name):
        _logger.info(_db_name)
        
        # Production DB name
        _db_name_prod = "https://www.r-e-a-l.it"

        # R-E-A-L.iT Master Database
        _master_database_template_id_prod = ("1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8")
        
        # Dev Numbers Set Based on When Developer Joined
        _master_database_template_id_dev_oli = ("1Nnvalaju0PvhlCDnaqsZ_vkMia8kMIQB4sqjAe7qY9Q")
        _master_database_template_id_dev_zek = ("1PyiopFOHqamiM66tQYB8CFVJ9KN2GIxPHUGaF-33xnU")   
        _master_database_template_id_dev_bc = ("133YJZivkWenwqh1UjwtLQlf4t6gxwrdXsEUW11ExWko")            
        
        # Return the proper GoogleSheet Template ID base on the environement
        if _db_name == _db_name_prod:
            _logger.info("Production")
            return _master_database_template_id_prod
        elif dev_oli in _db_name:
            _logger.info("Dev Oli")
            return _master_database_template_id_dev_oli
        elif dev_zek in _db_name:
            _logger.info("Dev Zek")
            return _master_database_template_id_dev_zek
        elif dev_braincrew in _db_name:
            _logger.info("Dev BrainCrew")
            return _master_database_template_id_dev_bc            
        else:
            _logger.info("Default Dev GS")
            return _master_database_template_id_prod

    # Methode to read a googlesheet document.
    # Input
    #   psw             : The password creedential to access the document.
    #   spreadsheetID   : The template_id of the googlesheet
    #   sheet_num       : The index of the sheet to read.

    def getDoc(self, psw, spreadsheetID, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = sac.from_json_keyfile_dict(psw, scope)
        client = gspread.authorize(creds)

        doc = client.open_by_key(spreadsheetID)
        return doc.get_worksheet(sheet_num).get_all_values()


    ###################################################################
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


    ###################################################################
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


    ###################################################################
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