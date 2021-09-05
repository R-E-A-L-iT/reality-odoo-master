# -*- coding: utf-8 -*-

import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials as sac

class sheetsAPI(model.Model):
    _name = sync.sheets
    _description = "Google Sheets API Handler"
    
    def getDoc(psw, spreadsheetID, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets"]

        creds = sac.from_json_keyfile_dict(psw, scope)
        client = gspread.authorize(creds)

