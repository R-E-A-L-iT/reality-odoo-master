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
        template_id = "12y6FkK_c95swZvqdwyNL-04cQFpqTGUGjJ1Syj-11_Y"
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
        syncType = ""
        while(True):
            
            if(str(req.json()["feed"]["entry"][i * 4 + 3]["content"]["$t"]) == "FALSE"):
                break
            sheetIndex = str(req.json()["feed"]["entry"][i * 4 + 1]["content"]["$t"])
            syncType = str(req.json()["feed"]["entry"][i * 4 + 2]["content"]["$t"])
            self.getSyncValues(template_id, sheetIndex, syncType)
            i = i + 1
        
    def getSyncValues(self, template_id, sheetIndex, syncType):
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
            self.syncCompanies(sheet)
        elif(syncType == "Contacts"):
            self.syncContacts(sheet)
            
    def syncCompanies(self, sheet):
        
        sheetWidth = 16
        i = 1
        r = ""
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) == "FALSE"):
                break;
            external_id = str(sheet[i * sheetWidth + 12]["content"]["$t"])
            company_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
            if(len(company_ids) > 0):
                self.updateCompany(self.env['res.partner'].browse(company_ids[len(company_ids) - 1].res_id), sheet, sheetWidth, i)
            else:
                self.createCompany(sheet, external_id, sheetWidth, i)
            
            i = i + 1
            
    def updateCompany(self, company, sheet, sheetWidth, i):
        
        company.name = sheet[i * sheetWidth]["content"]["$t"]
        company.phone = sheet[i * sheetWidth + 1]["content"]["$t"]
        company.website = sheet[i * sheetWidth + 2]["content"]["$t"]
        company.street = sheet[i * sheetWidth + 3]["content"]["$t"]
        company.city = sheet[i * sheetWidth + 4]["content"]["$t"]
        if(sheet[i * sheetWidth + 5]["content"]["$t"] != ""):
            company.state_id = int(self.env['res.country.state'].search([('code','=',sheet[i * sheetWidth + 5]["content"]["$t"])])[0].id)
        if(sheet[i * sheetWidth + 6]["content"]["$t"] != ""):
            company.country_id = int(self.env['res.country'].search([('name','=',sheet[i * sheetWidth + 6]["content"]["$t"])])[0].id)
        company.zip = sheet[i * sheetWidth + 7]["content"]["$t"]
        company.lang = sheet[i * sheetWidth + 8]["content"]["$t"]
        company.email = sheet[i * sheetWidth + 9]["content"]["$t"]
        if(sheet[i * sheetWidth + 10]["content"]["$t"] != ""):
            company.property_product_pricelist = int(self.env['product.pricelist'].search([('name','=',sheet[i * sheetWidth + 10]["content"]["$t"])])[0].id)
        company.is_company = True
        
    def createCompany(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"res.partner"})[0]
        company = self.env['res.partner'].create({'name': sheet[i * sheetWidth]["content"]["$t"]})[0]
        ext.res_id = company.id
        self.updateCompany(company, sheet, sheetWidth, i)
        
    def syncContacts(self, sheet):
    
        sheetWidth = 15
        i = 1
        r = ""
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) == "FALSE"):
                break;
            external_id = str(sheet[i * sheetWidth + 10]["content"]["$t"])

            contact_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
            if(len(contact_ids) > 0):
                contact = self.env['res.partner'].browse(contact_ids[len(contact_ids) - 1].res_id)[0]
                raise UserError(_("Contact: " + str(contact)))
                self.updateCompany(contact, sheet, sheetWidth, i)
            else:
                self.createCompany(sheet, external_id, sheetWidth, i)
            
            i = i + 1
            
    def updateContacts(self, contact, sheet, sheetWidth, i):
        
        contact.name = sheet[i * sheetWidth]["content"]["$t"]
        contact.phone = sheet[i * sheetWidth + 1]["content"]["$t"]
        contact.email = sheet[i * sheetWidth + 2]["content"]["$t"]
        #if(sheet[i * sheetWidth + 3]["content"]["$t"] != ""):
            #contact.parent_id = int(self.env['ir.model.data'].search([('name','=',sheet[i * sheetWidth + 3]["content"]["$t"]), ('model', '=', 'res.partner')])[0].res_id)
        contact.street = sheet[i * sheetWidth + 4]["content"]["$t"]
        contact.street = sheet[i * sheetWidth + 5]["content"]["$t"]
        #if(sheet[i * sheetWidth + 6]["content"]["$t"] != ""):
        #    contact.state_id = int(self.env['res.country.state'].search([('code','=',sheet[i * sheetWidth + 6]["content"]["$t"])])[0].id)
        #if(sheet[i * sheetWidth + 7]["content"]["$t"] != ""):
        #    contact.country_id = int(self.env['res.country'].search([('name','=',sheet[i * sheetWidth + 7]["content"]["$t"])])[0].id)
        contact.zip = sheet[i * sheetWidth + 8]["content"]["$t"]
        #if(sheet[i * sheetWidth + 9]["content"]["$t"] != ""):
        #    contact.property_product_pricelist = int(self.env['product.pricelist'].search([('name','=',sheet[i * sheetWidth + 9]["content"]["$t"])])[0].id)
        contact.is_company = False
        
    def createContacts(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"res.partner"})[0]
        contact = self.env['res.partner'].create({'name': sheet[i * sheetWidth]["content"]["$t"]})[0]
        ext.res_id = contact.id
        self.updateCompany(contact, sheet, sheetWidth, i)