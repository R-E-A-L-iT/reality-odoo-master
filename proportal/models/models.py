# -*- coding: utf-8 -*-

import ast
import base64
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
from urllib import request
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)



class productType(models.Model):
    _inherit = "product.template"
    skuhidden = fields.One2many("ir.model.data", "res_id", readonly=True)
    sku = fields.Char(related="skuhidden.name", string="SKU", readonly=True)
    storeCode = fields.Text(string="E-Commerce Store Code", default="")
    ecom_folder = fields.Char(string="folder", required=True, default="")
    ecom_media = fields.Char(string="Img Count", required=True, default="")


class person(models.Model):
    _inherit = "res.partner"

    # Identify Owned Products
    products = fields.One2many(
        "stock.production.lot", "owner", string="Products", readonly=True
    )
    parentProducts = fields.One2many(
        related="parent_id.products", string="Company Products", readonly=True
    )


class productInstance(models.Model):
    _inherit = "stock.production.lot"

    # Store Data For CCP Tracking
    owner = fields.Many2one("res.partner", string="Owner")
    equipment_number = fields.Char(string="Equipment Number")
    sku = fields.Char(related="product_id.sku", readonly=True, string="SKU")
    expire = fields.Date(
        string="Expiration Date",
        default=lambda self: fields.Date.today(),
        required=False,
    )
    formated_label = fields.Char(compute="_label")
    publish = fields.Boolean(string="publish", default="True")

    # Automate formated_label
    def _label(self):
        for i in self:
            parsedLabel = i.product_id.name.split(" - ")
            if len(parsedLabel) > 1:
                result = parsedLabel[1]
                for section in parsedLabel[2:]:
                    result = result + " - " + str(section)
                parsedLabel = result
            else:
                parsedLabel = parsedLabel[0]
            r = "#ccplabel+" + str(i.name) + "+" + str(parsedLabel)
            if i.expire != False:
                r = r + "+" + str(i.expire) 
            i.formated_label = r

            #return

# class ccp_status(models.Model):
#     _name = "product.ccp_status"
#     _description = "Leica status of each CCP in it's renewal process"
    
#     record_type = fields.Selection(
#         [("status_1", "Status 1"), ("status_2", "Status 2")], required=True, default="status_1"
#     )

class productBackend(models.Model):
    _inherit = "product.template"
    
    ccp_status = fields.Selection(
        [("basic", "Basic"),("blue", "Blue"),("bronze", "Bronze"),("silver", "Silver"),("gold", "Gold"),("expired", "Expired"),("none", "None")], string="CCP Status", default="none"
    )

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def init(self):
        internal_group = self.env.ref("base.group_user")
        portal_purchase_order_user_rule = self.env.ref(
            "purchase.portal_purchase_order_user_rule"
        )
        if portal_purchase_order_user_rule:
            portal_purchase_order_user_rule.sudo().write(
                {
                    "domain_force": "['|', ('message_partner_ids','child_of',[user.partner_id.id]),('partner_id', 'child_of', [user.partner_id.id])]"
                }
            )
        portal_purchase_order_line_rule = self.env.ref(
            "purchase.portal_purchase_order_line_rule"
        )
        if portal_purchase_order_line_rule:
            portal_purchase_order_line_rule.sudo().write(
                {
                    "domain_force": "['|',('order_id.message_partner_ids','child_of',[user.partner_id.id]),('order_id.partner_id','child_of',[user.partner_id.id])]"
                }
            )
        portal_purchase_order_comp_rule = self.env.ref(
            "purchase.purchase_order_comp_rule"
        )
        if portal_purchase_order_comp_rule and internal_group:
            portal_purchase_order_comp_rule.sudo().write(
                {"groups": [(4, internal_group.id)]}
            )
        portal_purchase_order_line_comp_rule = self.env.ref(
            "purchase.purchase_order_line_comp_rule"
        )
        if portal_purchase_order_line_comp_rule and internal_group:
            portal_purchase_order_line_comp_rule.sudo().write(
                {"groups": [(4, internal_group.id)]}
            )
        portal_project_comp_rule = self.env.ref("project.project_comp_rule")
        if portal_project_comp_rule and internal_group:
            portal_project_comp_rule.sudo().write({"groups": [(4, internal_group.id)]})
        portal_project_project_rule_portal = self.env.ref(
            "project.project_project_rule_portal"
        )
        if portal_project_project_rule_portal:
            portal_project_project_rule_portal.sudo().write(
                {
                    "domain_force": "['&', ('privacy_visibility', '=', 'portal'), ('partner_id', 'child_of', [user.partner_id.id])]"
                }
            )
        portal_task_comp_rule = self.env.ref("project.task_comp_rule")
        if portal_task_comp_rule and internal_group:
            portal_task_comp_rule.sudo().write({"groups": [(4, internal_group.id)]})
        portal_project_task_rule_portal = self.env.ref(
            "project.project_task_rule_portal"
        )
        if portal_project_task_rule_portal:
            portal_project_task_rule_portal.sudo().write(
                {
                    "domain_force": """[
		('project_id.privacy_visibility', '=', 'portal'),
		('active', '=', True),
		'|',
			('project_id.partner_id', 'child_of', [user.partner_id.id]),
			('partner_id', 'child_of', [user.partner_id.id]),
		]"""
                }
            )
        portal_account_move_comp_rule = self.env.ref("account.account_move_comp_rule")
        if portal_account_move_comp_rule and internal_group:
            portal_account_move_comp_rule.sudo().write(
                {"groups": [(4, internal_group.id)]}
            )
        portal_account_invoice_rule_portal = self.env.ref(
            "account.account_invoice_rule_portal"
        )
        if portal_account_invoice_rule_portal:
            portal_account_invoice_rule_portal.sudo().write(
                {
                    "domain_force": "[('move_type', 'in', ('out_invoice', 'out_refund', 'in_invoice', 'in_refund')), ('partner_id','child_of',[user.partner_id.id])]"
                }
            )

# remove available times that interfere with calendar events

# 1. triggered on selection of a specific day and employee in appointment booking, get array of every available time slot for that day
# 2. get list of all events for selected employee and selected day from calendar
# 3. check if any of the time slots overlap with existing calendar events
# 4. if so, remove them from view

class AppointmentView(models.Model):
    _inherit = "calendar.appointment.type"
    
    def overlap(first_start, first_end, second_start, second_end):
        #will check both ways
        for time in (first_start, first_end):
            if second_start < time < second_end:
                return True
            else:
                return False
    
    def removeConflictingTimes(self):
        for slot in slot_ids:
            for event in self.env['calendar.event'].sudo().search([]):
                if overlap(slot.start_datetime, slot.end_datetime, event.start, event.stop):
                    _logger.info("CALENDAR EVENT OVERLAP: TRUE")
                else:
                    _logger.info("CALENDAR EVENT OVERLAP: FALSE")
                    
    removeConflictingTimes()
            