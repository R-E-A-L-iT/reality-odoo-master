from .googlesheetsAPI import sheetsAPI
from odoo import api, fields, models, SUPERUSER_ID, _

import logging
_logger = logging.getLogger(__name__)


class reverse_sync_contacts(models.Model):
    _name = "sync.reverse_sync_contact"
    _description = "Reverse Contact Sync"

    def getSpreadSheetID(self):
        return "1pDPKv2bH8_Be5aCCyU4bqTuwJNcXsADlAYDAGG8P1Ls"

    def createHeader(self):
        return ["First Name", "Last Name", "Phone", "Email", "Company", "Street Address", "City", "State/Region", "Country", "Postal Code", "Industry", "Job Title", "Mobile"]

    def createRow(self, contact):
        return ['' for _ in range(contact)]

    def createBlank(self, length):
        return ['' for _ in range(length)]

    def reverseSync(self, psw):
        spreadSheetID = self.getSpreadSheetID()
        sheet = sheetsAPI.getSpreadSheet(spreadSheetID, sheetIndex=0, auth=psw)
        _logger.error(sheet.get_all_values())
        sheet.update('A1:M1', [self.createHeader()])
