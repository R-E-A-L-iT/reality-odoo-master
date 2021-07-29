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
    
    DatabaseURL = fields.Char(default="https://docs.google.com/spreadsheets/d/14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A/edit?usp=sharing")
    
    _description = "Sync App"
    def start_sync(self):
        _logger.info("Starting Sync")
        self.getCell()
        _logger.info("Ending Sync")
        
    def getCell(self):
        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_token = self.get_access_token()
        # Copy template in to drive with help of new access token
        request_url = "https://www.googleapis.com/drive/v2/files/%s/?access_token=%s&alt=media" % ("14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A", access_token)
        headers = {
            'Content-type': 'application/media',
            'Accept': 'text/plain'
        }
        try:
            res = requests.get(request_url,headers=headers, timeout=TIMEOUT)
            res.raise_for_status()
        except requests.HTTPError:
            raise UserError(_("The Google Document cannot be found"))
        raise UserError(_(str(res.json())))
        
    def sync_products(self):
        raise UserError("Not Implemented")
        
    def sync_ccp(self):
        raise UserError("Not Implemented")
    
    def sync_companies(self):
        raise UserError("Not Implemented")
        
    def sync_contacts(self):
        raise UserError("Not Implemented")