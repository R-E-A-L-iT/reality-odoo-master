# -*- coding: utf-8 -*-

from datetime import datetime
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredntials

import requests
from werkzeug import urls

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

TIMEOUT = 20

GOOGLE_AUTH_ENDPOINT = 'https://accounts.google.com/o/oauth2/auth'
GOOGLE_TOKEN_ENDPOINT = 'https://accounts.google.com/o/oauth2/token'
GOOGLE_API_BASE_URL = 'https://www.googleapis.com'

class googlesheetsAPI(models.AbstractModel):
    _name = "sync.sheets"
    _inherit = "google.service"
    _description = "Googlesheets API Handler"
    
    def _get_spreadsheet_tokens(self, refresh, id, secret):
        data = {
            'client_id': id,
            'refresh_token': refresh,
            'client_secret': secret,
            'grant_type': "refresh_token",
            'scope': 'https://www.googleapis.com/auth/spreadsheets'
        }
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            req = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
        except requests.HTTPError as e:
            raise UserError(_(str(e)))
            raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
        return req.json().get('access_token')