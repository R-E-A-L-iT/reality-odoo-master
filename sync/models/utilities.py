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
        _logger.error(date)
        if (date == False):
            return True
        return not (re.match(r'^\d{4}-\d{1,2}-\d{1,2}$', str(date)) is None)

    @staticmethod
    def buildMSG(msg: str, sheetName: str, key: str, problem: str):
        msg = msg + "<p>ERROR -> " + "Sheet: " + sheetName + \
            " | Item: " + key + " | " + problem + "</p>\n"
        return msg
