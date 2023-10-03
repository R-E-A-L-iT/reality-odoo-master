import logging
import re
_logger = logging.getLogger(__name__)


class utilities:
    @staticmethod
    def check_id(id):
        if (" " in id):
            _logger.info("ID: " + str(id))
            return False
        else:
            return True

    @staticmethod
    def check_price(price):
        if (price in ("", " ")):
            return True
        try:
            float(price)
            return True
        except Exception as e:
            _logger.info(e)
            return False

    @staticmethod
    def check_date(date) -> bool:
        if (str(date) == "FALSE"):
            return True
        return not (re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', str(date)) is None)

    @staticmethod
    def buildMSG(msg: str, sheetName: str, key: str, problem: str):
        msg = msg + "<p>ERROR -> " + "Sheet: " + str(sheetName) + \
            " | Item: " + str(key) + " | " + str(problem) + "</p>\n"
        return msg

    
    ##################################################
    # Check the header of a sheet to import data
    # Input
    #   pHeaderDict: a dictionary that hold the name of the google sheet row, and
    #                the name in the internal dictionnary
    #   p_sheet: the array of the GS sheet
    #   p_sheetName: the name of the sheet
    @staticmethod
    def checkSheetHeader(p_HeaderDict, p_sheet, p_sheetName):
        o_columns = dict()
        o_msg = ""
        o_columnsMissing = False        

        for row in p_HeaderDict:
            if row in p_sheet[0]:
                o_columns[p_HeaderDict[row]] = p_sheet[0].index(row)
            else:
                o_msg = utilities.buildMSG(o_msg, p_sheetName, "Header", str(row) + " Missing")
                o_columnsMissing = True

        return o_columns, o_msg, o_columnsMissing

