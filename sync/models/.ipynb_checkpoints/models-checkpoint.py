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
    
    DatabaseURL = fields.Char(default="https://docs.google.com/spreadsheets/d/14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A/edit?usp=sharing", string="DatabaseURL")
    
    _description = "Sync App"
    def start_sync(self):
        _logger.info("Starting Sync")
        self.test()
        _logger.info("Ending Sync")
        
    def getCell(self):
        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_token = self.get_access_token()
        # Copy template in to drive with help of new access token
        request_url = "https://www.googleapis.com/drive/v2/files/%s?fields=parents/id&access_token=%s" % ("14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A", access_token)
        try:
            res = requests.get(request_url)
        except requests.HTTPError:
            raise UserError(_("The Google Document cannot be found"))
        raise UserError(_(str(res.json()))
        
        
    def test(self):
        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_token = self.get_access_token()
        # Copy template in to drive with help of new access token
        request_url = "https://www.googleapis.com/drive/v2/files/%s?fields=parents/id&access_token=%s" % ("14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A", access_token)
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        try:
            req = requests.get(request_url, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
            parents_dict = req.json()
        except requests.HTTPError:
            raise UserError(_("The Google Document cannot be found. Maybe it has been deleted."))

        data = {
            "title": "Master Database",
            "description": "Master Database",
            "parents": parents_dict['parents']
        }
        request_url = "https://www.googleapis.com/drive/v2/files/%s/copy?access_token=%s" % ("14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A", access_token)
        headers = {
            'Content-type': 'application/json',
            'Accept': 'text/plain'
        }
        # resp, content = Http().request(request_url, "POST", data_json, headers)
        req = requests.post(request_url, data=json.dumps(data), headers=headers, timeout=TIMEOUT)
        req.raise_for_status()
        content = req.json()
        raise UserError(str(json.dumps(data)))
        
    def sync_products(self):
        raise UserError("Not Implemented")
        
    def sync_ccp(self):
        raise UserError("Not Implemented")
    
    def sync_companies(self):
        raise UserError("Not Implemented")
        
    def sync_contacts(self):
        raise UserError("Not Implemented")