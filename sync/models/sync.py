#-*- coding: utf-8 -*-

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import ast
import logging
import json
import re

import requests
import werkzeug.urls

from odoo.addons.google_account.models.google_service import GOOGLE_TOKEN_ENDPOINT, TIMEOUT

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import RedirectWarning, AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.tools.translate import _
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class sync(models.Model):
    _name = "sync.sync"
    _inherit = "google.drive.config"
    _description = "Sync App"

class sync(models.Model):
    _name = "sync.sync"
    
    _inherit = "google.drive.config"
    
    DatabaseURL = fields.Char(default="https://docs.google.com/spreadsheets/d/14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A/edit?usp=sharing")
    
    _description = "Sync App"
    
    def start_sync(self):
        _logger.info("Starting Sync")
        self.getSyncData()
        _logger.info("Ending Sync")
        
    def getSyncData(self):
        template_id = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"
        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_token = self.get_access_token()

        request_url = "https://spreadsheets.google.com/feeds/cells/%s/1/private/full?access_token=%s&alt=json" % (template_id, access_token)
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            req = requests.get(request_url, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
        except requests.HTTPError:
            raise UserError(_("Invalid Document"))
        i = 1
        sheetIndex = ""
        sheetWidth = 0
        syncType = ""
        while(True):
            
            if(str(req.json()["feed"]["entry"][i * 5 + 4]["content"]["$t"]) == "FALSE"):
                break
            sheetIndex = str(req.json()["feed"]["entry"][i * 5 + 1]["content"]["$t"])
            sheetWidth = int(req.json()["feed"]["entry"][i * 5 + 2]["content"]["$t"])
            syncType = str(req.json()["feed"]["entry"][i * 5 + 3]["content"]["$t"])
            self.getSyncValues(sheetIndex, sheetWidth, syncType)
            i = i + 1
        
    def getSyncValues(self, sheetIndex, sheetWidth, syncType):
        template_id = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"
        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_token = self.get_access_token()

        request_url = "https://spreadsheets.google.com/feeds/cells/%s/%s/private/full?access_token=%s&alt=json" % (template_id, sheetIndex, access_token)
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        
        try:
            req = requests.get(request_url, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
        except requests.HTTPError:
            raise UserError(_("Invalid Document"))
        sheet = req.json()["feed"]["entry"]
        
        if(syncType == "Companies"):
            self.syncCompanies(sheet, sheetWidth)
            
    def syncCompanies(self, sheet, sheetWidth):
        i = 1
        r = ""
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) == "FALSE"):
                break;
            j = 0
            while(j < sheetWidth):
                r = r + str(sheet[i * sheetWidth + j)]["content"]["$t"]) + "    "
                j = j + 1
            r = r + "\n"
        raise UserError("r")