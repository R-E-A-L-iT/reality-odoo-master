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
