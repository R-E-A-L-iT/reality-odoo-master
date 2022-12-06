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
    _master_database_template_id = "17qHJGr_dhUm7B_hKYuKS32nQ1-5iIWBqVhtkHOEb5ls"
    
    def getDoc(self, psw, spreadsheetID, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = sac.from_json_keyfile_dict(psw, scope)
        client = gspread.authorize(creds)
        
        doc = client.open_by_key(spreadsheetID)
        return doc.get_worksheet(sheet_num).get_all_values()

