#-*- coding: utf-8 -*-

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class sync(models.Model):
    _name = "sync.sync"
    
    _inherit = "google.drive.config"
    
    DatabaseURL = fields.Char(default="https://docs.google.com/spreadsheets/d/14XrvJUaWddKFIEV3eYZvcCtAyzkvdNDswsREgUxiv_A/edit?usp=sharing", string="DatabaseURL")
    
    _description = "Sync App"
    def start_sync(self):
        _logger.info("Starting Sync")
        self.get_access_token()
        _logger.info("Ending Sync")
        
    def sync_products(self):
        raise UserError("Not Implemented")
        
    def sync_ccp(self):
        raise UserError("Not Implemented")
    
    def sync_companies(self):
        raise UserError("Not Implemented")
        
    def sync_contacts(self):
        raise UserError("Not Implemented")