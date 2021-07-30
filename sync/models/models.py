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
    
    def start_sync(self):
        _logger.info("Start Sync")
        fileID = "1ZoT9NZ1pJEtYWRavImwsYPnccTxGB51e34qcDo9cclU"
        accsess_token = self.get_access_token()
        headers = {
            'Accept': 'application/json',
        }
        requestURL = "/v4/spreadsheets/%s?includeGridData=true&ranges=Sheet1!a1:d2&accsess_token&key=%s" % (fileID, accsess_token, "AIzaSyD5qi35QEIb-e76OnNqOiAECz7aD4xm3PI")
        raise UserError(_(str(self.env['google.service']._do_request(requestURL, headers=headers, method="GET"))))

#class sync(models.Model):
#    _name = "sync.sync"
#    
#    _inherit = "google.drive.config"
    
#    DatabaseURL = fields.Char(default="https://docs.google.com/spreadsheets/d/14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A/edit?usp=sharing")
    
#    _description = "Sync App"
#    def start_sync(self):
#        _logger.info("Starting Sync")
#        self.getCell()
#        _logger.info("Ending Sync")
#        
#    def getCell(self):
#        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
#        access_token = self.get_access_token()
#        sheetID = "1ZoT9NZ1pJEtYWRavImwsYPnccTxGB51e34qcDo9cclU"
#        # Copy template in to drive with help of new access token
#        request_url = "https://www.googleapis.com/drive/v2/files/%s/?access_token=%s" % (sheetID, access_token)
#        #request_url = "https://sheets.googleapis.com/v4/spreadsheets/%s?includeGridData=true&ranges=Sheet1!a1:d2&fields=sheets.data.rowData.values.formattedValue&accsess_token=%s" % (sheetID, access_token)
#        headers = {
#            'Accept': 'application/json',
#            'Authorization': "Bearer %s" % (access_token)
#        }
#        try:
#            res = requests.get(request_url,headers=headers, timeout=TIMEOUT)
#            #raise UserError(_("Here"))
#            #res.raise_for_status()
#        except requests.HTTPError:
#            raise UserError(_("The Google Document cannot be found"))
#        raise UserError(_(str(res.json())))
#        
#    def get_access_token(self, scope=None):
#        Config = self.env['ir.config_parameter'].sudo()
#        google_drive_refresh_token = Config.get_param('google_drive_refresh_token')
#        user_is_admin = self.env.is_admin()
#        if not google_drive_refresh_token:
#            if user_is_admin:
#                dummy, action_id = self.env['ir.model.data'].get_object_reference('base_setup', 'action_general_configuration')
#                msg = _("There is no refresh code set for Google Drive. You can set it up from the configuration panel.")
#                raise RedirectWarning(msg, action_id, _('Go to the configuration panel'))
#            else:
#                raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
#        google_drive_client_id = Config.get_param('google_drive_client_id')
#        google_drive_client_secret = Config.get_param('google_drive_client_secret')
#        #For Getting New Access Token With help of old Refresh Token
#        data = {
#            'client_id': google_drive_client_id,
#            'refresh_token': google_drive_refresh_token,
#            'client_secret': google_drive_client_secret,
#            'grant_type': "refresh_token",
#            'scope': scope or 'https://www.googleapis.com/auth/drive'
#        }
#        headers = {"Content-type": "application/x-www-form-urlencoded"}
#        try:
#            req = requests.post(GOOGLE_TOKEN_ENDPOINT, data=data, headers=headers, timeout=TIMEOUT)
#            req.raise_for_status()
#        except requests.HTTPError:
#            if user_is_admin:
#                dummy, action_id = self.env['ir.model.data'].get_object_reference('base_setup', 'action_general_configuration')
#                msg = _("Something went wrong during the token generation. Please request again an authorization code .")
#                raise RedirectWarning(msg, action_id, _('Go to the configuration panel'))
#            else:
#                raise UserError(_("Google Drive is not yet configured. Please contact your administrator."))
#        raise UserError(_(str(req.json())))
#        return req.json()
#    def sync_products(self):
#        raise UserError("Not Implemented")
#        
#    def sync_ccp(self):
#        raise UserError("Not Implemented")
#    
#    def sync_companies(self):
#        raise UserError("Not Implemented")
#        
#    def sync_contacts(self):
#        raise UserError("Not Implemented")