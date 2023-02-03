# -*- coding: utf-8 -*-
import gspread

from odoo import api, fields, models
from odoo.exceptions import UserError
from oauth2client.service_account import ServiceAccountCredentials as sac

# Prefixes Used in Branches To Differentiate Branches
dev1_prefix = "Dev_Ty_"
dev2_prefix = "Dev_Oli_"


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
        # Production DB name
        _db_name_prod = "https://www.r-e-a-l.it"

        # R-E-A-L.iT Master Database
        _master_database_template_id_prod = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"

        # Dev Numbers Set Based on When Developer Joined
        # _master_database_template_id_dev1 = "1UT2h8r8ut3tB4icPKLJwO6d6qfEr2Oca8Vv6po3yYEc"
        _master_database_template_id_dev1 = "1UT2h8r8ut3tB4icPKLJwO6d6qfEr2Oca8Vv6po3yYEc"
        # DEV R-E-A-L.iT Master Database

        _master_database_template_id_dev2 = "1PeClDoVPC7yx8C1d8ShQkz0AlUZrBYVwBJfYZKYzcIU"

        # Return the proper GoogleSheet Template ID base on the environement
        if (_db_name == _db_name_prod):
            return _master_database_template_id_prod
        elif (dev1_prefix in _db_name):
            return _master_database_template_id_dev1
        elif (dev2_prefix in _db_name):
            return _master_database_template_id_dev2
        else:
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
