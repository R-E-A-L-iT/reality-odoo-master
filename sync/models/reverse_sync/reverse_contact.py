from .googlesheetsAPI import sheetsAPI

import logging
_logger = logging.getLogger(__name__)


class reverse_sync_contacts():
    def getSpreadSheetID(self):
        return "1pDPKv2bH8_Be5aCCyU4bqTuwJNcXsADlAYDAGG8P1Ls"

    def reverseSync(self, psw):
        spreadSheetID = self.getSpreadSheetID()
        sheet = sheetsAPI.getSpreadSheet(spreadSheetID, sheetIndex=0, auth=psw)
        _logger.error(sheet.get_all_values())
