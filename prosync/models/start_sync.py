import gspread
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError
from oauth2client.service_account import ServiceAccountCredentials as sac

from .sync.product_template import product_template_sync
from .sync.stock_lot import stock_lot_sync
from .sync.res_partner import res_partner_sync

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
    def get_master_database_template_id(self, _db_name):

        config = self.env['ir.config_parameter'].sudo()
        prod_id = config.get_param('prosync.production_sheet_id')
        dev_id = config.get_param('prosync.development_sheet_id')
        
        _db_name_prod = "https://www.r-e-a-l.it"

        if "dev" in _db_name:
            _logger.info("\n-----------------\nProSync\nStarting sync on development data\n-----------------")
            return dev_id
        else:
            _logger.info("\n-----------------\nProSync\nStarting sync on production data\n-----------------")
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
            db_name = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            template_id = self.get_master_database_template_id(db_name)
            configuration_tab = self.establish_sheets_connection(pw, template_id, 0)

            # Loop throw configuration sheet rows
            while line_index < len(configuration_tab):

                row = configuration_tab[line_index]
                if len(row) < 6:
                    _logger.info("ProSync: Skipping incomplete or empty row.")
                    line_index += 1
                    continue

                sheet_name = str(configuration_tab[line_index][0])
                sheet_index = str(configuration_tab[line_index][1])
                sheet_type = str(configuration_tab[line_index][2])
                sheet_date = datetime.strptime(configuration_tab[line_index][3].strip(), "%d/%m/%Y")
                sheet_valid = (str(configuration_tab[line_index][4]).upper() == "TRUE")
                sheet_continue = (str(configuration_tab[line_index][5]).upper() == "TRUE")

                if sheet_valid:
                    if sheet_date.date() > datetime.today().date():
                        _logger.info("ProSync: Skipping scheduled sheet.")
                        line_index += 1
                        continue

                    if sheet_type == "product_template":
                        _logger.info(f"ProSync: Processing sheet of type: {sheet_type}")
                        
                        sheet_data = self.establish_sheets_connection(pw, template_id, int(sheet_index))

                        syncer = product_template_sync(name=sheet_name, sheet=sheet_data, database=self.env)
                        syncer.sync_product_template()
                    elif sheet_type == "stock_lot":
                        _logger.info(f"ProSync: Processing sheet of type: {sheet_type}")

                        sheet_data = self.establish_sheets_connection(pw, template_id, int(sheet_index))
                        syncer = stock_lot_sync(name=sheet_name, sheet=sheet_data, database=self.env)
                        syncer.sync_stock_lot()
                    elif sheet_type == "res_partner":
                        _logger.info(f"ProSync: Processing sheet of type: {sheet_type}")

                        sheet_data = self.establish_sheets_connection(pw, template_id, int(sheet_index))
                        syncer = res_partner_sync(name=sheet_name, sheet=sheet_data, database=self.env)
                        syncer.sync_res_partner()
                    else:
                        _logger.error(f"ProSync: Given sheet type is not supported by ProSync: {sheet_type}")

                    line_index += 1
                    continue

                elif sheet_continue:
                    _logger.info("ProSync: Invalid row but CONTINUE is TRUE. Skipping to next.")
                    line_index += 1
                    continue
                else:
                    _logger.info("ProSync: Invalid row and CONTINUE is FALSE. Ending sync.")
                    break

        finally:
            _logger.info("\n-----------------\nProSync\nEnding sync process\n-----------------")