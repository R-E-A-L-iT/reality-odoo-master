# -*- coding: utf-8 -*-

import json
import gspread

from odoo import api, fields, models
from odoo.exceptions import UserError
from oauth2client.service_account import ServiceAccountCredentials as sac

class sheetsAPI(models.Model):

    def __init__(self):
        self.name =  "sync.sheets"
        self._inherit = "google.drive.config"
        self._description = "Google Sheets API Handler"
        self._db_name = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        self._db_name_prod = "https://www.r-e-a-l.it"

        # R-E-A-L.iT Master Database
        _master_database_template_id_prod = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"

        # DEV R-E-A-L.iT Master Database
        _master_database_template_id_dev = "1E454v0jC2NpkfTENpc-OT0Uh2EW4U3fFVZecwmFGDTc"

        #Set the proper GoogleSheet Template ID base on the environement
        if (self._db_name == self._db_name_prod):
            self._master_database_template_id = _master_database_template_id_prod
        else:
            self._master_database_template_id = _master_database_template_id_dev  

    def getDoc(self, psw, spreadsheetID, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = sac.from_json_keyfile_dict(psw, scope)
        client = gspread.authorize(creds)
        
        doc = client.open_by_key(spreadsheetID)
        return doc.get_worksheet(sheet_num).get_all_values()

    def get_master_database_template_id(self):
        return self._master_database_template_id



    