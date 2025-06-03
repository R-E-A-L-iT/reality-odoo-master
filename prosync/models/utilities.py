import logging
import re
from datetime import datetime, date, timedelta
_logger = logging.getLogger(__name__)

# normalization functions and report related functions
class utilities:
    
    # -- ODOO FIELD TYPES --
    # 
    # SUPPORTED BY SYNC:
    # 
    #   char, text, html
    #   integer, float, boolean
    #   date, datetime
    #   monetary
    #   binary (images, files, signatures)
    # 
    # UNSUPPORTED BY SYNC:
    # 
    #   selection
    #   many2one, many2many, one2many


    # char normalization function
    def normalize_char(self, value):
        _logger.log("ProSync | Normalizing char value: %s", value)

    # text normalization function
    def normalize_text(self, value):
        _logger.log("ProSync | Normalizing text value: %s", value)

    # html normalization function
    def normalize_html(self, value):
        _logger.log("ProSync | Normalizing html value: %s", value)

    # integer normalization function
    def normalize_integer(self, value):
        _logger.log("ProSync | Normalizing integer value: %s", value)