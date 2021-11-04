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

# Insert code to catch when a customer views a quote here

# example?..:
# 
# sendQuoteNotification(
#     "R-E-A-L.iT | A Client has Viewed your Quote",
#     "Ezekiel deBlois has viewed your quotation with the ID of S0174.",
#     ["ezekiel@r-e-a-l.it", "derek@r-e-a-l.it"]
# )
#
#

# Function to create a quote notification email and send 

def sendQuoteNotification(self, title, msg, recipients):
    
    values = {'subject': title}
    values = {'mail_message_id': message.id}
    
    message = self.env['mail.message'].create(values)[0]
    
    email = self.env['mail.mail'].create(values)[0]
    email_id = {email.id}
    email.body_html = msg
    
    for user in recipients:
        
        this.email.email_to = String(user)
        
    email_id.process_email_queue(email_id)