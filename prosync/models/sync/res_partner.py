
# -*- coding: utf-8 -*-

import re
import logging

from ..utilities import (
    normalize_char,
    normalize_text,
    normalize_date,
    normalize_float,
    normalize_integer,
    normalize_bool,
    normalize_binary,
    normalize_selection,
    normalize_many2one,
    normalize_many2many,
    update_with_lang_context,
)

_logger = logging.getLogger(__name__)

class res_partner_sync:

    def __init__(self, name, sheet, database):
        self.name = name
        self.sheet = sheet
        self.database = database

    def sync_res_partner(self):
        _logger.info("ProSync: Starting RES_PARTNER sync process.")