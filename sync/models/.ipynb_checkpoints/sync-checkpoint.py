# -*- coding: utf-8 -*-

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
    
    _inherit = "sync.sheets"
    
    DatabaseURL = fields.Char(default="")
    
    _description = "Sync App"
    
    def start_sync(self, code=None):
        _logger.info("Starting Sync")
        self.getSyncData(code)
        _logger.info("Ending Sync")
        
    def getSyncData(self, code):
        
        template_id = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"
        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_token, ignore, ignore = self._get_google_tokens(code, "spreadsheets")
        request_url = "https://sheets.googleapis.com/v4/spreadsheets/%s" % (template_id)
        headers = {"Accept": "Application/json",
                  "Authorization": "OAuth %s" % (access_token)}
        try:
            req = requests.get(request_url, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
        except requests.HTTPError:
            msg = "<h1>Source Document Invalid<\h1><p>Sync Fail</p>"
            self.sendSyncReport(msg)
            raise UserError(_(req.json()))
            raise UserError(_("Invalid Main Document"))
        i = 1
        sheetIndex = ""
        syncType = ""
        msg = ""
        while(True):
            if(str(req.json()["feed"]["entry"][i * 4 + 3]["content"]["$t"]) != "TRUE"):
                break
                
            sheetIndex = str(req.json()["feed"]["entry"][i * 4 + 1]["content"]["$t"])
            syncType = str(req.json()["feed"]["entry"][i * 4 + 2]["content"]["$t"])
            quit, msgr = self.getSyncValues(template_id, sheetIndex, syncType)
            msg = msg + msgr
            i = i + 1
            if(quit):
                self.syncCancel(msg)
                return
        if(msg != ""):
            self.syncFail(msg)
            
    def getSyncValues(self, template_id, sheetIndex, syncType):
        google_web_base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        access_token = self.get_access_token()

        request_url = "https://spreadsheets.google.com/feeds/cells/%s/%s/private/full?access_token=%s&alt=json" % (template_id, sheetIndex, access_token)
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        
        msg = ""
        try:
            req = requests.get(request_url, headers=headers, timeout=TIMEOUT)
            req.raise_for_status()
        except requests.HTTPError:
            msg = ("<h1>Source Document Invalid<\h1><p>Page: %s</p><p>Sync Fail</p>" % sheetIndex) 
            self.sendSyncReport(msg)
            raise UserError(_("Invalid Sheet: %s" % sheetIndex))
        sheet = req.json()["feed"]["entry"]
        
        if(syncType == "Companies"):
            _logger.info("Companies")
            quit, msg = self.syncCompanies(sheet)
        elif(syncType == "Contacts"):
            _logger.info("Contacts")
            quit, msg = self.syncContacts(sheet)
        elif(syncType == "Products"):
            _logger.info("Products")
            quit, msg = self.syncProducts(sheet)
        elif(syncType == "CCP"):
            _logger.info("CCP")
            quit, msg = self.syncCCP(sheet)
        elif(syncType == "Pricelist"):
            _logger.info("Pricelist")
            quit, msg = self.syncPricelist(sheet)
        return quit, msg
            
    def syncCompanies(self, sheet):
        
        sheetWidth = 16
        i = 1
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) != "TRUE"):
                break
            if(not self.check_id(str(sheet[i * sheetWidth + 12]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
            try:
                external_id = str(sheet[i * sheetWidth + 12]["content"]["$t"])
                company_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
                if(len(company_ids) > 0):
                    self.updateCompany(self.env['res.partner'].browse(company_ids[len(company_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createCompany(sheet, external_id, sheetWidth, i)
            except:
                _logger.info("Companies")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
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
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) != "TRUE"):
                break
            if(not self.check_id(str(sheet[i * sheetWidth + 10]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
                
            if(not self.check_id(str(sheet[i * sheetWidth + 3]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
            try:
                external_id = str(sheet[i * sheetWidth + 10]["content"]["$t"])
            
                contact_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
                if(len(contact_ids) > 0):
                    self.updateContacts(self.env['res.partner'].browse(contact_ids[len(contact_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createContacts(sheet, external_id, sheetWidth, i)
            except:
                _logger.info("Contacts")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
    def updateContacts(self, contact, sheet, sheetWidth, i):
        contact.name = sheet[i * sheetWidth]["content"]["$t"]
        contact.phone = sheet[i * sheetWidth + 1]["content"]["$t"]
        contact.email = sheet[i * sheetWidth + 2]["content"]["$t"]
        if(sheet[i * sheetWidth + 3]["content"]["$t"] != ""):
            contact.parent_id = int(self.env['ir.model.data'].search([('name','=',sheet[i * sheetWidth + 3]["content"]["$t"]), ('model', '=', 'res.partner')])[0].res_id)
        contact.street = sheet[i * sheetWidth + 4]["content"]["$t"]
        contact.city = sheet[i * sheetWidth + 5]["content"]["$t"]
        if(sheet[i * sheetWidth + 6]["content"]["$t"] != ""):
            contact.state_id = int(self.env['res.country.state'].search([('code','=',sheet[i * sheetWidth + 6]["content"]["$t"])])[0].id)
        if(sheet[i * sheetWidth + 7]["content"]["$t"] != ""):
            contact.country_id = int(self.env['res.country'].search([('name','=',sheet[i * sheetWidth + 7]["content"]["$t"])])[0].id)
        contact.zip = sheet[i * sheetWidth + 8]["content"]["$t"]
        if(sheet[i * sheetWidth + 9]["content"]["$t"] != ""):
            contact.property_product_pricelist = int(self.env['product.pricelist'].search([('name','=',sheet[i * sheetWidth + 9]["content"]["$t"])])[0].id)
        contact.is_company = False
        
    def createContacts(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"res.partner"})[0]
        contact = self.env['res.partner'].create({'name': sheet[i * sheetWidth]["content"]["$t"]})[0]
        ext.res_id = contact.id
        self.updateContacts(contact, sheet, sheetWidth, i)
        
    def syncProducts(self, sheet):
    
        sheetWidth = 7
        i = 1
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) != "TRUE"):
                break
            if(not self.check_id(str(sheet[i * sheetWidth]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_price(sheet[i * sheetWidth + 3]["content"]["$t"])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
            
            try:
                external_id = str(sheet[i * sheetWidth]["content"]["$t"])
            
                product_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'product.template')])
                if(len(product_ids) > 0):
                    self.updateProducts(self.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createProducts(sheet, external_id, sheetWidth, i)
            except:
                _logger.info("Products")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
    def updateProducts(self, product, sheet, sheetWidth, i):
        product.name = sheet[i * sheetWidth + 1]["content"]["$t"]
        product.description_sale = sheet[i * sheetWidth + 2]["content"]["$t"]
        product.price = sheet[i * sheetWidth + 3]["content"]["$t"]
        product.tracking = "serial"
        product.type = "product"
        
    def createProducts(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"product.template"})[0]
        product = self.env['product.template'].create({'name': sheet[i * sheetWidth + 1]["content"]["$t"]})[0]
        ext.res_id = product.id
        self.updateProducts(product, sheet, sheetWidth, i)
        
    def syncCCP(self, sheet):
    
        sheetWidth = 9
        i = 1
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) != "TRUE"):
                break
            if(str(sheet[i * sheetWidth + 6]["content"]["$t"]) != "TRUE"):
                i = i + 1
                continue

            if(not self.check_id(str(sheet[i * sheetWidth + 2]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            try:
                external_id = str(sheet[i * sheetWidth + 2]["content"]["$t"])
            
                ccp_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'stock.production.lot')])
                if(len(ccp_ids) > 0):
                    self.updateCCP(self.env['stock.production.lot'].browse(ccp_ids[len(ccp_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createCCP(sheet, external_id, sheetWidth, i)
            except:
                _logger.info("CCP")
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg

            
    def updateCCP(self, ccp_item, sheet, sheetWidth, i):
        ccp_item.name = sheet[i * sheetWidth + 1]["content"]["$t"]
        
        product_ids = self.env['product.product'].search([('name', '=', sheet[i * sheetWidth + 4]["content"]["$t"])])
        ccp_item.product_id = product_ids[len(product_ids) - 1].id
        owner_ids = self.env['ir.model.data'].search([('name', '=', sheet[i * sheetWidth]["content"]["$t"]), 
                                                          ('model', '=', 'res.partner')])
        ccp_item.owner = owner_ids[len(owner_ids) - 1].res_id
        if(sheet[i * sheetWidth + 5]["content"]["$t"] != "FALSE"):
            ccp_item.expire = sheet[i * sheetWidth + 5]["content"]["$t"]
        else:
            ccp_item.expire = None
        
    def createCCP(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"stock.production.lot"})[0]
        
        product_ids = self.env['product.product'].search([('name', '=', sheet[i * sheetWidth + 4]["content"]["$t"])])
        
        product_id = product_ids[len(product_ids) - 1].id
        
        company_id = self.env['res.company'].search([('id', '=', 1)]).id
        
        ccp_item = self.env['stock.production.lot'].create({'name': sheet[i * sheetWidth + 1]["content"]["$t"],
                                                            'product_id': product_id, 'company_id': company_id})[0]
        ext.res_id = ccp_item.id
        self.updateCCP(ccp_item, sheet, sheetWidth, i)
        
    def syncPricelist(self, sheet):
        sheetWidth = 19
        i = 1
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i * sheetWidth + (sheetWidth - 1)]["content"]["$t"]) != "TRUE"):
                break
            if(str(sheet[i * sheetWidth + 17]["content"]["$t"]) != "TRUE"):
                i = i + 1
                continue
            
            if(not self.check_id(str(sheet[i * sheetWidth]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_id(str(sheet[i * sheetWidth + 14]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_id(str(sheet[i * sheetWidth + 16]["content"]["$t"]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_price(sheet[i * sheetWidth + 5]["content"]["$t"])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_price(sheet[i * sheetWidth + 6]["content"]["$t"])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            try:
                product = self.pricelistProduct(sheet, sheetWidth, i)
                self.pricelistCAN(product, sheet, sheetWidth, i)
                self.pricelistUS(product, sheet, sheetWidth, i)
            except:
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                return True, msg
            
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
    def pricelistProduct(self, sheet, sheetWidth, i):
        external_id = str(sheet[i * sheetWidth]["content"]["$t"])  
        product_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'product.template')])
        if(len(product_ids) > 0): 
            return self.updatePricelistProducts(self.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i)
        else:
            return self.createPricelistProducts(sheet, external_id, sheetWidth, i)
    
    def pricelistCAN(self, product, sheet, sheetWidth, i):
        external_id = str(sheet[i * sheetWidth + 14]["content"]["$t"])
        pricelist_id = self.env['product.pricelist'].search([('name','=','CAN Pricelist')])[0].id
        pricelist_item_ids = self.env['product.pricelist.item'].search([('product_tmpl_id','=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0): 
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i * sheetWidth + 5]["content"]["$t"]) != " " and str(sheet[i * sheetWidth + 5]["content"]["$t"]) != ""):
                pricelist_item.fixed_price = sheet[i * sheetWidth + 5]["content"]["$t"]
        else:
            pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i * sheetWidth + 5]["content"]["$t"]) != " " and str(sheet[i * sheetWidth + 5]["content"]["$t"]) != ""):
                pricelist_item.fixed_price = sheet[i * sheetWidth + 5]["content"]["$t"]
    
    def pricelistUS(self, product, sheet, sheetWidth, i):
        external_id = str(sheet[i * sheetWidth + 16]["content"]["$t"])
        pricelist_id = self.env['product.pricelist'].search([('name','=','USD Pricelist')])[0].id
        pricelist_item_ids = self.env['product.pricelist.item'].search([('product_tmpl_id','=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0): 
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i * sheetWidth + 6]["content"]["$t"]) != " " and str(sheet[i * sheetWidth + 5]["content"]["$t"]) != ""):
                pricelist_item.fixed_price = sheet[i * sheetWidth + 6]["content"]["$t"]
        else:
            pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i * sheetWidth + 6]["content"]["$t"]) != " " and str(sheet[i * sheetWidth + 5]["content"]["$t"]) != ""):
                pricelist_item.fixed_price = sheet[i * sheetWidth + 6]["content"]["$t"]
    
    def updatePricelistProducts(self, product, sheet, sheetWidth, i, new=False):
        product.name = sheet[i * sheetWidth + 1]["content"]["$t"]
        product.description_sale = sheet[i * sheetWidth + 2]["content"]["$t"]
        
        if(str(sheet[i * sheetWidth + 5]["content"]["$t"]) != " " and str(sheet[i * sheetWidth + 5]["content"]["$t"]) != ""):
            product.price = sheet[i * sheetWidth + 5]["content"]["$t"]
        
        if(str(sheet[i * sheetWidth + 10]["content"]["$t"]) == "TRUE"):
            product.is_published = True
        else:
            product.is_published = False
        product.tracking = "serial"
        product.type = "product"
        
        self.translatePricelistFrench(product, sheet, sheetWidth, i, new)
        
        return product
        
    def translatePricelistFrench(self, product, sheet, sheetWidth, i, new):
        if(new == True):
            return
        else:
            product_name_french = self.env['ir.translation'].search([('res_id', '=', product.id),
                                                                     ('name', '=', 'product.template,name'),
                                                                    ('lang', '=', 'fr_CA')])

            if(len(product_name_french) > 0):
                product_name_french[len(product_name_french) - 1].value = sheet[i * sheetWidth + 3]["content"]["$t"]

            else:
                product_name_french_new = self.env['ir.translation'].create({'name':'product.template,name', 
                                                                            'lang':'fr_CA',
                                                                            'res_id': product.id})[0]
                product_name_french_new.value = sheet[i * sheetWidth + 3]["content"]["$t"]
            

            product_description_french = self.env['ir.translation'].search([('res_id', '=', product.id),
                                                                     ('name', '=', 'product.template,description_sale'),
                                                                    ('lang', '=', 'fr_CA')])

            if(len(product_description_french) > 0):
                product_description_french[len(product_description_french) - 1].value = sheet[i * sheetWidth + 4]["content"]["$t"]
            else:
                product_description_french_new = self.env['ir.translation'].create({'name':'product.template,description_sale', 
                                                                            'lang':'fr_CA',
                                                                            'res_id': product.id})[0]
                product_description_french_new.value = sheet[i * sheetWidth + 4]["content"]["$t"]
            return
    
    def createPricelistProducts(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"product.template"})[0]
        product = self.env['product.template'].create({'name': sheet[i * sheetWidth + 1]["content"]["$t"]})[0]
        ext.res_id = product.id
        self.updatePricelistProducts(product, sheet, sheetWidth, i, new=True)
        return product
    
    def check_id(self, id):
        if(" " in id):
            _logger.info("ID: " + str(id))
            return False
        else:
            return True
    
    def check_price(self, price):
        if(price in ("", " ")):
            return True
        try:
            float(price)
            return True
        except:
            return False
            _logger.info("Price: " + str(price))
    
    def buildMSG(self, msg, sheet, sheetWidth, i):
        if(msg == ""):
            msg = self.startTable(msg, sheet, sheetWidth, True)
        msg = msg + "<tr>"
        j = 0
        while(j < sheetWidth):
            msg = msg + "<td>" + str(sheet[sheetWidth * i + j]["content"]["$t"])
            j = j + 1
        msg = msg + "</tr>"
        return msg
            
    def startTable(self, msg, sheet, sheetWidth, force=False):
        if(force):
            msg = msg + "<table><tr>"
            j = 0
            while(j < sheetWidth):
                msg = msg + "<th><strong>" + str(sheet[j]["content"]["$t"]) + "</strong></th>"
                j = j + 1
            msg = msg + "</tr>"
        elif(msg != ""):
            msg = msg + "<table><tr>"
            while(j < sheetWidth):
                msg = msg + "<th>" + str(sheet[j]["content"]["$t"]) + "</th>"
                j = j + 1
            msg = msg + "</tr>"
            
        return msg
    
    def endTable(self, msg):
        if(msg != ""):
            msg = msg + "</table>"
        return msg
            
    
    def syncCancel(self, msg):
        link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
        msg = "<h1>The Sync Procsess Was forced to quit and no records were updated</h1><h1> The Following Rows of The Google Sheet Table are invalid<h1>" + msg + "<a href=\"" + link + "\">Manual Retry</a>"
        _logger.info(msg)
        self.sendSyncReport(msg)
    
    def syncFail(self, msg):
        link = "https://www.r-e-a-l.store/web?debug=assets#id=34&action=12&model=ir.cron&view_type=form&cids=1%2C3&menu_id=4"
        msg = "<h1>The Following Rows of The Google Sheet Table are invalid and were not Updated to Odoo</h1>" + msg + "<a href=\"" + link + "\">Manual Retry</a>"
        _logger.info(msg)
        self.sendSyncReport(msg)
    
    def sendSyncReport(self, msg):
        values = {'subject': 'Sync Report'}
        message = self.env['mail.message'].create(values)[0]
        
        values = {'mail_message_id': message.id}
        
        email = self.env['mail.mail'].create(values)[0]
        email.body_html = msg
        email.email_to = "ezekiel@r-e-a-l.it"
        email_id = {email.id}
        email.process_email_queue(email_id)        
