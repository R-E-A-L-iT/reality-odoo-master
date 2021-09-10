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
    
    def start_sync(self, psw=None):
        _logger.info("Starting Sync")
        if(psw == None):
            msg = "<h1>Sync Error</h1><p>Authentication values Missing</p>"
            _logger.info(msg)
            self.sendSyncReport(msg)
            return
        self.getSyncData(psw)
        _logger.info("Ending Sync")
        
    def getSyncData(self, psw):
        
        template_id = "1Tbo0NdMVpva8coych4sgjWo7Zi-EHNdl6EFx2DZ6bJ8"
        
        try:
            sync_data = self.getDoc(psw, template_id, 0)
        except Exception as e:
            _logger.info(e)
            msg = "<h1>Source Document Invalid<\h1><p>Sync Fail</p>"
            self.sendSyncReport(msg)
            return
        i = 1
        sheetIndex = ""
        syncType = ""
        msg = ""
        while(True):
            if(str(sync_data[i][3]) != "TRUE"):
                break
                
            sheetIndex = int(sync_data[i][1])
            syncType = str(sync_data[i][2])
            
            quit, msgr = self.getSyncValues(psw, template_id, sheetIndex, syncType)
            msg = msg + msgr
            i = i + 1
            if(quit):
                self.syncCancel(msg)
                return
        if(msg != ""):
            self.syncFail(msg)
            
    def getSyncValues(self, psw, template_id, sheetIndex, syncType):
        try:
            sheet = self.getDoc(psw, template_id, sheetIndex)
        except Exception as e:
            _logger.info(e)
            msg = ("<h1>Source Document Invalid<\h1><p>Page: %s</p><p>Sync Fail</p>" % sheetIndex) 
            self.sendSyncReport(msg)
            return False, ""
        
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
        if(len(sheet[i]) != sheetWidth):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            return
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i][-1]) != "TRUE"):
                break
            
            if(not self.check_id(str(sheet[i][12]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
            
            try:
                external_id = str(sheet[i][12])
                company_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
                if(len(company_ids) > 0):
                    self.updateCompany(self.env['res.partner'].browse(company_ids[len(company_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createCompany(sheet, external_id, sheetWidth, i)
            except Exception as e:
                _logger.info("Companies")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
    def updateCompany(self, company, sheet, sheetWidth, i):
        
        if(company.stringRep == str(sheet[i][:])):
            return
        company.stringRep = str(sheet[i][:])
        
        company.name = sheet[i][0]
        company.phone = sheet[i][1]
        company.website = sheet[i][2]
        company.street = sheet[i][3]
        company.city = sheet[i][4]
        if(sheet[i][5] != ""):
            company.state_id = int(self.env['res.country.state'].search([('code','=',sheet[i][5])])[0].id)
        name = sheet[i][6]
        if(name != ""):
            if(name == "US"):
                name = "United States"
            company.country_id = int(self.env['res.country'].search([('name','=', name)])[0].id)
        company.zip = sheet[i][7]
        company.lang = sheet[i][8]
        company.email = sheet[i][9]
        if(sheet[i][10] != ""):
            company.property_product_pricelist = int(self.env['product.pricelist'].search([('name','=',sheet[i][10])])[0].id)
        company.is_company = True
        
    def createCompany(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"res.partner"})[0]
        company = self.env['res.partner'].create({'name': sheet[i][0]})[0]
        ext.res_id = company.id
        self.updateCompany(company, sheet, sheetWidth, i)
        
    def syncContacts(self, sheet):
    
        sheetWidth = 15
        i = 1
        if(len(sheet[i]) != sheetWidth):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            return
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i][-1]) != "TRUE"):
                break
            if(not self.check_id(str(sheet[i][10]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
                
            if(not self.check_id(str(sheet[i][3]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
            try:
                external_id = str(sheet[i][10])
            
                contact_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'res.partner')])
                if(len(contact_ids) > 0):
                    self.updateContacts(self.env['res.partner'].browse(contact_ids[len(contact_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createContacts(sheet, external_id, sheetWidth, i)
            except Exception as e:
                _logger.info("Contacts")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
    def updateContacts(self, contact, sheet, sheetWidth, i):
        
        if(contact.stringRep == str(sheet[i][:])):
            return
        contact.stringRep = str(sheet[i][:])
        
        contact.name = sheet[i][0]
        contact.phone = sheet[i][1]
        contact.email = sheet[i][2]
        if(sheet[i][3] != ""):
            contact.parent_id = int(self.env['ir.model.data'].search([('name','=',sheet[i][3]), ('model', '=', 'res.partner')])[0].res_id)
        contact.street = sheet[i][4]
        contact.city = sheet[i][5]
        if(sheet[i][6] != ""):
            contact.state_id = int(self.env['res.country.state'].search([('code','=',sheet[i][6])])[0].id)
        
        name = sheet[i][7]
        if(name != ""):
            if(name == "US"):
                name = "United States"
            contact.country_id = int(self.env['res.country'].search([('name','=',name)])[0].id)
        contact.zip = sheet[i][8]
        if(sheet[i][9] != ""):
            contact.property_product_pricelist = int(self.env['product.pricelist'].search([('name','=',sheet[i][9])])[0].id)
        contact.is_company = False
        
    def createContacts(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"res.partner"})[0]
        contact = self.env['res.partner'].create({'name': sheet[i][0]})[0]
        ext.res_id = contact.id
        self.updateContacts(contact, sheet, sheetWidth, i)
        
    def syncProducts(self, sheet):
    
        sheetWidth = 7
        i = 1
        if(len(sheet[i]) != sheetWidth):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            return
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i][-1]) != "TRUE"):
                break
            if(not self.check_id(str(sheet[i][0]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_price(sheet[i][3])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
            
            try:
                external_id = str(sheet[i][0])
            
                product_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'product.template')])
                if(len(product_ids) > 0):
                    self.updateProducts(self.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createProducts(sheet, external_id, sheetWidth, i)
            except Exception as e:
                _logger.info("Products")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
    def updateProducts(self, product, sheet, sheetWidth, i):
        
        if(product.stringRep == str(sheet[i][:])):
            return
        product.stringRep = str(sheet[i][:])
        
        product.name = sheet[i][1]
        product.description_sale = sheet[i][2]
        product.price = sheet[i][3]
        product.tracking = "serial"
        product.type = "product"
        
    def createProducts(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"product.template"})[0]
        product = self.env['product.template'].create({'name': sheet[i][1]})[0]
        ext.res_id = product.id
        self.updateProducts(product, sheet, sheetWidth, i)
        
    def syncCCP(self, sheet):
    
        sheetWidth = 9
        i = 1
        if(len(sheet[i]) != sheetWidth):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            return
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i][-1]) != "TRUE"):
                break
            if(str(sheet[i][6]) != "TRUE"):
                i = i + 1
                continue

            if(not self.check_id(str(sheet[i][2]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            try:
                external_id = str(sheet[i][2])
            
                ccp_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'stock.production.lot')])
                if(len(ccp_ids) > 0):
                    self.updateCCP(self.env['stock.production.lot'].browse(ccp_ids[len(ccp_ids) - 1].res_id), sheet, sheetWidth, i)
                else:
                    self.createCCP(sheet, external_id, sheetWidth, i)
            except Exception as e:
                _logger.info("CCP")
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                msg = self.endTable(msg)
                return True, msg
            i = i + 1
        msg = self.endTable(msg)
        return False, msg

            
    def updateCCP(self, ccp_item, sheet, sheetWidth, i):
        
        if(ccp_item.stringRep == str(sheet[i][:])):
            return
        ccp_item.stringRep = str(sheet[i][:])
        
        ccp_item.name = sheet[i][1]
        
        product_ids = self.env['product.product'].search([('name', '=', sheet[i][4])])
        ccp_item.product_id = product_ids[len(product_ids) - 1].id
        owner_ids = self.env['ir.model.data'].search([('name', '=', sheet[i][0]), 
                                                          ('model', '=', 'res.partner')])
        ccp_item.owner = owner_ids[len(owner_ids) - 1].res_id
        if(sheet[i][5] != "FALSE"):
            ccp_item.expire = sheet[i][5]
        else:
            ccp_item.expire = None
        
    def createCCP(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"stock.production.lot"})[0]
        
        product_ids = self.env['product.product'].search([('name', '=', sheet[i][4])])
        
        product_id = product_ids[len(product_ids) - 1].id
        
        company_id = self.env['res.company'].search([('id', '=', 1)]).id
        
        ccp_item = self.env['stock.production.lot'].create({'name': sheet[i][1],
                                                            'product_id': product_id, 'company_id': company_id})[0]
        ext.res_id = ccp_item.id
        self.updateCCP(ccp_item, sheet, sheetWidth, i)
        
    def syncPricelist(self, sheet):
        sheetWidth = 19
        i = 1
        if(len(sheet[i]) != sheetWidth):
            msg = "<h1>Sync Page Invalid<h1>"
            self.sendSyncReport(msg)
            return
        r = ""
        msg = ""
        msg = self.startTable(msg, sheet, sheetWidth)
        while(True):
            if(str(sheet[i][sheetWidth - 1]) != "TRUE"):
                break
            if(str(sheet[i][17]) != "TRUE"):
                i = i + 1
                continue
            
            if(not self.check_id(str(sheet[i][0]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_id(str(sheet[i][14]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_id(str(sheet[i][16]))):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_price(sheet[i][5])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            if(not self.check_price(sheet[i][6])):
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                i = i + 1
                continue
               
            try:
                product = self.pricelistProduct(sheet, sheetWidth, i)
                if(product.stringRep == str(sheet[i][:])):
                    i = i + 1
                    continue
                product.stringRep = str(sheet[i][:])
                self.pricelistCAN(product, sheet, sheetWidth, i)
                self.pricelistUS(product, sheet, sheetWidth, i)
            except Exception as e:
                _logger.info(e)
                msg = self.buildMSG(msg, sheet, sheetWidth, i)
                return True, msg
            
            i = i + 1
        msg = self.endTable(msg)
        return False, msg
            
    def pricelistProduct(self, sheet, sheetWidth, i):
        external_id = str(sheet[i][0])  
        product_ids = self.env['ir.model.data'].search([('name','=', external_id), ('model', '=', 'product.template')])
        if(len(product_ids) > 0): 
            return self.updatePricelistProducts(self.env['product.template'].browse(product_ids[len(product_ids) - 1].res_id), sheet, sheetWidth, i)
        else:
            return self.createPricelistProducts(sheet, external_id, sheetWidth, i)
    
    def pricelistCAN(self, product, sheet, sheetWidth, i):
        external_id = str(sheet[i][14])
        pricelist_id = self.env['product.pricelist'].search([('name','=','CAN Pricelist')])[0].id
        pricelist_item_ids = self.env['product.pricelist.item'].search([('product_tmpl_id','=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0): 
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][5]) != " " and str(sheet[i][5]) != ""):
                pricelist_item.fixed_price = sheet[i][5]
        else:
            pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][5]) != " " and str(sheet[i][5]) != ""):
                pricelist_item.fixed_price = sheet[i][5]
    
    def pricelistUS(self, product, sheet, sheetWidth, i):
        external_id = str(sheet[i][16])
        pricelist_id = self.env['product.pricelist'].search([('name','=','USD Pricelist')])[0].id
        pricelist_item_ids = self.env['product.pricelist.item'].search([('product_tmpl_id','=', product.id), ('pricelist_id', '=', pricelist_id)])
        if(len(pricelist_item_ids) > 0): 
            pricelist_item = pricelist_item_ids[len(pricelist_item_ids) - 1]
            pricelist_item.product_tmpl_id = product.id
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][6]) != " " and str(sheet[i][6]) != ""):
                pricelist_item.fixed_price = sheet[i][6]
        else:
            pricelist_item = self.env['product.pricelist.item'].create({'pricelist_id':pricelist_id, 'product_tmpl_id':product.id})[0]
            pricelist_item.applied_on = "1_product"
            if(str(sheet[i][6]) != " " and str(sheet[i][6]) != ""):
                pricelist_item.fixed_price = sheet[i][6]
    
    def updatePricelistProducts(self, product, sheet, sheetWidth, i, new=False):
        
        if(product.stringRep == str(sheet[i][:])):
            return product
        if(not new):
            product.stringRep = str(sheet[i][:])
        
        product.name = sheet[i][1]
        product.description_sale = sheet[i][2]
        
        if(str(sheet[i][5]) != " " and str(sheet[i][5]) != ""):
            product.price = sheet[i][5]
        
        if(str(sheet[i][10]) == "TRUE"):
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
                product_name_french[len(product_name_french) - 1].value = sheet[i][3]

            else:
                product_name_french_new = self.env['ir.translation'].create({'name':'product.template,name', 
                                                                            'lang':'fr_CA',
                                                                            'res_id': product.id})[0]
                product_name_french_new.value = sheet[i][3]
            

            product_description_french = self.env['ir.translation'].search([('res_id', '=', product.id),
                                                                     ('name', '=', 'product.template,description_sale'),
                                                                    ('lang', '=', 'fr_CA')])

            if(len(product_description_french) > 0):
                product_description_french[len(product_description_french) - 1].value = sheet[i][4]
            else:
                product_description_french_new = self.env['ir.translation'].create({'name':'product.template,description_sale', 
                                                                            'lang':'fr_CA',
                                                                            'res_id': product.id})[0]
                product_description_french_new.value = sheet[i][4]
            return
    
    def createPricelistProducts(self, sheet, external_id, sheetWidth, i):
        ext = self.env['ir.model.data'].create({'name': external_id, 'model':"product.template"})[0]
        product = self.env['product.template'].create({'name': sheet[i][1]})[0]
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
        except Exception as e:
            _logger.info(e)
            return False
    
    def buildMSG(self, msg, sheet, sheetWidth, i):
        if(msg == ""):
            msg = self.startTable(msg, sheet, sheetWidth, True)
        msg = msg + "<tr>"
        j = 0
        while(j < sheetWidth):
            msg = msg + "<td>" + str(sheet[i][j])
            j = j + 1
        msg = msg + "</tr>"
        return msg
            
    def startTable(self, msg, sheet, sheetWidth, force=False):
        if(force):
            msg = msg + "<table><tr>"
            j = 0
            while(j < sheetWidth):
                msg = msg + "<th><strong>" + str(sheet[0][j]) + "</strong></th>"
                j = j + 1
            msg = msg + "</tr>"
        elif(msg != ""):
            msg = msg + "<table><tr>"
            while(j < sheetWidth):
                msg = msg + "<th>" + str(sheet[0][j]) + "</th>"
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
        
        
        #Send another Sync Report
        values = {'subject': 'Sync Report'}
        message = self.env['mail.message'].create(values)[0]
        
        values = {'mail_message_id': message.id}
        
        email = self.env['mail.mail'].create(values)[0]
        email.body_html = msg
        email.email_to = "tyjcyr@gmail.com"
        email_id = {email.id}
        email.process_email_queue(email_id)   
