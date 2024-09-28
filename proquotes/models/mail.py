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
    
    @api.model
    def get_tracking_url(self, name, target_url):
        
        # target_url = "https://erp.gyeongcc.com" + record.get_portal_url()
        link_tracker = self.env['link.tracker'].sudo().search([('url', '=', target_url)], limit=1)
        if not link_tracker:
            try:
                link_tracker = self.env['link.tracker'].sudo().create({
                    'title': name,
                    'url': target_url,
                })
                
                _logger.info("link tracker created successfully")
                return link_tracker.short_url
            except:
                _logger.info("exception occured.")
                return target_url
        else:
            return link_tracker.short_url

    @api.model_create_multi
    def create(self, values_list):
        messages = super(MailMessage, self).create(values_list)
        for message in messages:
            if message.model=='sale.order' and message.res_id and message.body:
                order = self.env['sale.order'].sudo().browse(int(message.res_id))
                if order:
                    body = message.body
                    
                    # bottom_footer = _("\r\n \r\n Quotation: %s") % (str(self.get_base_url()) + "/my/orders/" + str(order.sudo().id) + "?access_token=" + str(order.sudo().access_token))
                    
                    url = str(self.get_base_url()) + "/my/orders/" + str(order.sudo().id) + "?access_token=" + str(order.sudo().access_token)
                    
                    bottom_footer = _("\r\n \r\n Quotation: %s") % (self.get_tracking_url("Quotation: " + str(order.sudo().name), url))
                    
                    # link = (str(self.get_base_url()) + "/my/orders/" + str(order.sudo().id) + "?access_token=" + str(order.sudo().access_token))
                    
                    # html_data = """<a style='color:red;' href='""" + link + """'>View Quote</a> """
                    
                    # bottom_footer = _("\n Quotation: " + html_data)
                    
                    body = body + bottom_footer
                    message.body = body
            elif message.model=='slide.channel' and message.res_id and message.body:
                body = message.body
                course = self.env['slide.channel'].sudo().browse(int(message.res_id))
                if course:
                    
                    url = course.sudo().website_url
                    
                    footer = _("\r\n \r\n Course: %s") % (self.get_tracking_url("Course: " + str(course.sudo().display_name), url))
                    
                    body = body + footer
                    message.body = body
            
            # if message is for ticket, add link to bottom but also add signature that is the same html every time but swap out email address to be address of employee sending email.        
            
            elif message.model=='project.task' and message.res_id and message.body:
                body = message.body
                task = self.env['project.task'].sudo().browse(int(message.res_id))
                if task:
                    
                    url = str(self.get_base_url() + task.sudo().access_url)
                    
                    footer = str("\r\n \r\n Task: " + str(self.get_tracking_url("Task: " + str(task.sudo().display_name), url)))
                    
                    body = body + footer
                    message.body = body
                    
        return messages
