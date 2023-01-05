# -*- coding: utf-8 -*-

import json
import gspread

from odoo import api, fields, models
from odoo.exceptions import UserError
from oauth2client.service_account import ServiceAccountCredentials as sac

class sheetsAPI(models.Model):
    _name = "sync.sheets"
    _inherit = "google.drive.config"
    _description = "Google Sheets API Handler"
    
    # R-E-A-L.iT Master Database
    # 1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8
    # 
    # DEV R-E-A-L.iT Master Database
    # 1E454v0jC2NpkfTENpc-OT0Uh2EW4U3fFVZecwmFGDTc

    
    _master_database_template_id = "1E454v0jC2NpkfTENpc-OT0Uh2EW4U3fFVZecwmFGDTc"
    
    def getDoc(self, psw, spreadsheetID, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = sac.from_json_keyfile_dict(psw, scope)
        client = gspread.authorize(creds)
        
        doc = client.open_by_key(spreadsheetID)
        return doc.get_worksheet(sheet_num).get_all_values()




