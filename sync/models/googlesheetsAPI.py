# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging

import requests
from werkzeug import urls

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

TIMEOUT = 20

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'

class googlesheetsAPI(models.AbstractModel):
    _name = "sync.sheets"
    _inherit = "google.drive.config"