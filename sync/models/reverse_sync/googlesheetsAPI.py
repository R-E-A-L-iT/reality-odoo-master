import gspread
from oauth2client.service_account import ServiceAccountCredentials as sac


class sheetsAPI():
    @staticmethod
    def getSpreadSheet(spreadSheetID, sheetIndex, auth):
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = sac.from_json_keyfile_dict(auth, scope)
        client = gspread.authorize(creds)
        doc = client.open_by_key(spreadSheetID)
        return doc.getWorksheet(sheetIndex)
