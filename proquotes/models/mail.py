# -*- coding: utf-8 -*-

import ast
import base64
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


class mail(models.TransientModel):
    _inherit = "mail.compose.message"

    def get_mail_values(self, res_ids):
        # Force 'reply_to' to be the same as 'email_from'
        result = super().get_mail_values(res_ids)
        for key in result:
            result[key]["reply_to"] = result[key]["email_from"]
            result[key]["reply_to_force_new"] = True
        return result

class MailMessage(models.Model):
    _inherit = 'mail.message'
    
    @api.model
    def get_base_url(self):
        return self.env['ir.config_parameter'].sudo().get_param('web.base.url')

    @api.model_create_multi
    def create(self, values_list):
        messages = super(MailMessage, self).create(values_list)
        for message in messages:
            if message.model=='sale.order' and message.res_id and message.body:
                order = self.env['sale.order'].sudo().browse(int(message.res_id))
                if order:
                    body = message.body
                    
                    # bottom_footer = _("\r\n \r\n Quotation: %s") % (str(self.get_base_url()) + "/my/orders/" + str(order.sudo().id) + "?access_token=" + str(order.sudo().access_token))
                    
                    link = (str(self.get_base_url()) + "/my/orders/" + str(order.sudo().id) + "?access_token=" + str(order.sudo().access_token))
                    
                    html_data = """<a style='color:red;' href='""" + html_data + """'>View Quote</a> """
                    
                    bottom_footer = _("\n Quotation: " + html_data)
                    
                    body = body + bottom_footer
                    message.body = body
        return messages
