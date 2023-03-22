from .googlesheetsAPI import sheetsAPI
from odoo import api, fields, models, SUPERUSER_ID, _

import logging
_logger = logging.getLogger(__name__)


class reverse_sync_contacts(models.Model):
    _name = "sync.reverse_sync"

    def getSpreadSheetID(self):
        return "1pDPKv2bH8_Be5aCCyU4bqTuwJNcXsADlAYDAGG8P1Ls"

    def reverseSync(self, psw):
        spreadSheetID = self.getSpreadSheetID()
        sheet = sheetsAPI.getSpreadSheet(spreadSheetID, sheetIndex=0, auth=psw)
        _logger.error(sheet.get_all_values())
