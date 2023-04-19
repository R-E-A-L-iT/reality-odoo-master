import gspread
from oauth2client.service_account import ServiceAccountCredentials as sac
import logging

_logger = logging.getLogger(__name__)


class sheetsAPI:
    @staticmethod
    def getSpreadSheet(spreadSheetID, sheetIndex, auth):
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = sac.from_json_keyfile_dict(auth, scope)
        client = gspread.authorize(creds)
        doc = client.open_by_key(spreadSheetID)
        return doc.get_worksheet(sheetIndex)

    @staticmethod
    def getSpreadSheetByName(spreadSheetID, sheetName, auth):
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = sac.from_json_keyfile_dict(auth, scope)
        client = gspread.authorize(creds)
        doc = client.open_by_key(spreadSheetID)
        tabs = list(map(lambda item: item.title, doc.worksheets()))
        if sheetName not in tabs:
            return None
        return doc.worksheet(sheetName)
