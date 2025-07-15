import gspread
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from oauth2client.service_account import ServiceAccountCredentials as sac

from datetime import datetime

_logger = logging.getLogger(__name__)

# Step 1. Establish Google Sheets connection
# - Retrieve Sheet ID for production and development stored in system parametres
# - Retrieve API Key stored in system parametres and establish connection
# - Connect to Google sheets API and confirm that the sheet is readable
class ProsyncSync(models.Model):
    _name = "prosync.sync"
    _description = "Sync model for ProSync"

    # - Retrieve Sheet ID stored in system parametres
    @staticmethod
    def get_master_database_template_id(_db_name):

        config = self.env['ir.config_parameter'].sudo()
        prod_id = config.get_param('prosync.production_sheet_id')
        dev_id = config.get_param('prosync.development_sheet_id')
        
        _db_name_prod = "https://www.r-e-a-l.it"

        if "dev" in _db_name:
            _logger.info("-----------------\nProSync\nStarting sync on development data\n-----------------")
            return dev_id
        else:
            _logger.info("-----------------\nProSync\nStarting sync on production data\n-----------------")
            return prod_id

    # - Retrieve API Key stored in system parametres and establish connection
    def establish_sheets_connection(self, pw, sheet_id, sheet_num):
        scope = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

        creds = sac.from_json_keyfile_dict(pw, scope)
        client = gspread.authorize(creds)

        doc = client.open_by_key(sheet_id)
        return doc.get_worksheet(sheet_num).get_all_values()

    # Step 2. Read ODOO_CONFIGURATION tab
    # - For each row, check first if valid
    # - - If not valid, check if continue
    # - - - If not continue, end sync
    # - - - If continue, check next row
    # - - If valid, check if date less than or equal to current date
    # - - - If not less than or equal to current date, skip to next row
    # - - - If less than or equal to current date, check for tab with matching index and name
    # - - - - If found, process tab
    # - - - - If not found, error and check next row
    def start_sync_process(self, pw=None):
        try:
            line_index = 1
            configuration_tab = self.establish_sheets_connection(pw, template_id, 0)

            # Loop throw configuration sheet rows
            while True:
                sheet_name = str(configuration_tab[line_index][0])
                sheet_index = str(configuration_tab[line_index][1])
                sheet_type = str(configuration_tab[line_index][2])
                sheet_date = datetime.strptime(configuration_tab[line_index][3].strip(), "%d/%m/%Y")
                sheet_valid = (str(configuration_tab[line_index][4]).upper() == "TRUE")
                sheet_continue = (str(configuration_tab[line_index][5]).upper() == "TRUE")

                _logger.info("ProSync: " + sheet_name)
                _logger.info("ProSync: " + sheet_index)
                _logger.info("ProSync: " + sheet_type)
                _logger.info("ProSync: " + sheet_date)
                _logger.info("ProSync: " + sheet_valid)
                _logger.info("ProSync: " + sheet_continue)

                line_index += 1

        finally:
            _logger.info("-----------------\nProSync\nEnding sync process\n-----------------")