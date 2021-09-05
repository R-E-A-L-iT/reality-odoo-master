# -*- coding: utf-8 -*-

import json
import gspread

from odoo import api, fields, models
from oauth2client.service_account import ServiceAccountCredentials as sac

class sheetsAPI(models.Model):
    _name = "sync.sheets"
    _description = "Google Sheets API Handler"
    
    def getDoc(self, psw, spreadsheetID, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets"]

        creds = sac.from_json_keyfile_dict(psw, scope)
        client = gspread.authorize(creds)
        
        doc = client.open_by_key(spreadsheetID)
        raise UserError(str(doc.get_all_values()))

