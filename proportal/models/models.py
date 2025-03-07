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
    sku = fields.Char(related="skuhidden.name", string="SKU")
    storeCode = fields.Text(string="E-Commerce Store Code", default="")
    ecom_folder = fields.Char(string="folder", required=True, default="")
    ecom_media = fields.Char(string="Img Count", required=True, default="")

    @api.model
    def create(self, vals):
        record = super(productType, self).create(vals)
        if "sku" in vals:
            self._update_skuhidden(record.id, vals["sku"], record.name)
        return record

    def write(self, vals):
        result = super(productType, self).write(vals)
        if "sku" in vals:
            for record in self:
                self._update_skuhidden(record.id, vals["sku"], record.name)
        return result

    def _update_skuhidden(self, record_id, sku_value, record_name):
        IrModelData = self.env["ir.model.data"]
        data = IrModelData.search([("res_id", "=", record_id), ("model", "=", "product.template")], limit=1)
        if data:
            data.write({"name": sku_value, "display_name": record_name})
        else:
            IrModelData.create({"name": sku_value, "module": "",
                                "model": "product.template", "res_id": record_id,
                                "display_name": record_name,
                                })

class visitor(models.Model):
    _inherit = 'website.visitor'

    ip_address = fields.Char(string="IP Address", help="The IP address of the visitor")

class person(models.Model):
    _inherit = "res.partner"

    # Identify Owned Products
    # products = fields.One2many(
        # "stock.lot", domain="'|', ('owner', '=', res.partner)", readonly=True
    # )
    products = fields.One2many(
        "stock.lot", "owner", string="Products", readonly=True
    )
    parentProducts = fields.One2many(
        related="parent_id.products", string="Company Products", readonly=True
    )


class productInstance(models.Model):
    _inherit = "stock.lot"

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

    firmware_version = fields.Text(string='Firmware Version', help='Firmware version associated with this lot.')

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

