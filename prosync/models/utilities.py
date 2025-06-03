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

    # float normalization function
    def normalize_float(self, value):
        _logger.log("ProSync | Normalizing float value: %s", value)

    # integer normalization function
    def normalize_boolean(self, value):
        _logger.log("ProSync | Normalizing boolean value: %s", value)



    # date normalization function
    def normalize_date(self, value):
        _logger.log("ProSync | Normalizing date value: %s", value)

    # datetime normalization function
    def normalize_datetime(self, value):
        _logger.log("ProSync | Normalizing datetime value: %s", value)

    # monetary normalization function
    def normalize_monetary(self, value):
        _logger.log("ProSync | Normalizing monetary value: %s", value)

    # binary normalization function
    def normalize_binary(self, value):
        _logger.log("ProSync | Normalizing binary value: %s", value)



    # in the future maybe add limited support for Many2one, Many2many, One2many fields (like product_type for example)