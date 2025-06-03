from odoo import models, api
from oauth2client.service_account import ServiceAccountCredentials as sac
import gspread
import json
import logging

_logger = logging.getLogger(__name__)

class SyncGoogleSheets(models.Model):
    _name = 'prosync.sync'
    _description = 'Base model for ProSync functions'

    # fetch credentials from system parameters
    def get_credentials(self):
        param = self.env['ir.config_parameter'].sudo().get_param('prosync.credentials')
        if not param:
            raise ValueError("ProSync | Google Sheets credentials not set in system parameters.")
        return json.loads(param)

    # fetch correct google sheet from system parameters
    def get_master_database_template_id(self):
        return self.env['ir.config_parameter'].sudo().get_param('prosync.sheet_id')

    # function to return all data from individual tabs of google sheet
    def get_sheet_data(self, spreadsheet_id, sheet_index=0):
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        creds_dict = self._get_credentials()
        creds = sac.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        doc = client.open_by_key(spreadsheet_id)
        return doc.get_worksheet(sheet_index).get_all_values()

    # starting point of the sync scheduled action
    def start_sync(self):
        _logger.info("ProSync | Starting scheduled sheet sync")
        spreadsheet_id = self.get_master_database_template_id()
        sheet_data = self.get_sheet_data(spreadsheet_id, 0)
        # Example:
        # self.env['product.template'].create({...})
        _logger.info("ProSync | Ending scheduled sheet sync")

