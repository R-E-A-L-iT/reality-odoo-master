# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
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

class orderLineProquotes(models.Model):
    _inherit = "sale.order.line"

    variant = fields.Many2one("proquotes.variant", string="Variant Group")

    # applied_name = fields.Char(compute="get_applied_name", string="Applied Name")
    applied_name = fields.Char(string="Applied Name")

    selected = fields.Selection(
        [("true", "Yes"), ("false", "No")],
        default="true",
        required=True,
        help="Field to Mark Wether Customer has Selected Product",
    )

    sectionSelected = fields.Selection(
        [("true", "Yes"), ("false", "No")],
        default="true",
        required=True,
        help="Field to Mark Wether Container Section is Selected",
    )

    special = fields.Selection(
        [("regular", "regular"), ("multiple", "Multiple"), ("optional", "Optional")],
        default="regular",
        required=True,
        help="Technical field for UX purpose.",
    )

    hiddenSection = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        default="no",
        required=True,
        help="Field To Track if Sections are folded",
    )

    optional = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        default="no",
        required=True,
        help="Field to Mark Product as Optional",
    )

    quantityLocked = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Lock Quantity",
        default="yes",
        required=True,
        help="Field to Lock Quantity on Products",
    )

    is_optional = fields.Boolean(
        required=True, string="Optional",
        help="Field to Mark Product as Optional",
    )
    is_selected = fields.Boolean(
        required=True, string="Selected",
        help="Field to Mark Wether Customer has Selected Product",
    )
    is_quantityLocked = fields.Boolean(
        string="Lock Quantity",
        required=True,
        help="Field to Lock Quantity on Products",
    )

    demo_selected = fields.Boolean(string="Selected", compute="_check_selected_line",
                                   help="Field to Mark Wether Customer has Selected Product",
                                   )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.order_id and line.order_id.sale_order_template_id.name.lower() == 'sales blank':
                line.is_selected = True
            else:
                line.is_selected = False
                
    @api.onchange('is_selected', 'is_quantityLocked', 'is_optional')
    def _onchange_selected_line(self):
        if self.is_selected:
            self.selected = 'true'
        else:
            self.selected = 'false'
        if self.is_quantityLocked:
            self.quantityLocked = 'yes'
        else:
            self.quantityLocked = 'no'
        if self.is_optional:
            self.optional = 'yes'
        else:
            self.optional = 'no'
    def _check_selected_line(self):
        for rec in self:
            rec.demo_selected = False
            rec.is_quantityLocked = False
            if rec.selected == 'true':
                rec.is_selected = True
            else:
                rec.is_selected = False
            if rec.optional == 'yes':
                rec.is_optional = True
            else:
                rec.is_optional = False
            if rec.quantityLocked == 'yes':
                rec.is_quantityLocked = True
            else:
                rec.is_quantityLocked = False

    def get_sale_order_line_multiline_description_sale(self, product):
        if product.description_sale:
            return product.description_sale
        else:
            return "<span></span>"

    @api.depends('product_uom_qty', 'selected', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            tax_results = self.env['account.tax'].with_company(line.company_id)._compute_taxes([
                line._convert_to_tax_base_line_dict()
            ])
            totals = list(tax_results['totals'].values())[0]
            if line.selected == 'false' or line.product_uom_qty == 0:
                amount_untaxed = 0.00
                _logger.info('>>>>>>>>>>iff>>>>>>.amount_untaxed: %s,', amount_untaxed)

            else:
                amount_untaxed = totals['amount_untaxed']
                _logger.info('>>>>>>>>else>>>>>>>>. amount_untaxed: %s,', amount_untaxed)
            amount_tax = totals['amount_tax']

            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

class PreconfigSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    preconfigured_section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')