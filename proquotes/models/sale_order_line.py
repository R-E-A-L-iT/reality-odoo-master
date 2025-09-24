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

    @api.onchange('product_id', 'order_id.is_rental')
    def _onchange_product_id(self):
        for line in self:
            if line.order_id.is_rental and line.product_id:
                target_categories = [
                    'Software (Permanent License)',
                    'Software CCP',
                    'Software Subscription'
                ]
                if line.product_id.categ_id and line.product_id.categ_id.name in target_categories:
                    line.price_unit = line.product_id.list_price
                else:
                    line.price_unit = line.product_id.lst_price
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

    def _prepare_procurement_values(self, group_id=False):
        """
        Override to handle renewal products with serial numbers.
        For Renewal Auto template, modify the procurement values to use the correct product
        from stock.lot if a match is found.
        """
        values = super(orderLineProquotes, self)._prepare_procurement_values(group_id)
        
        # Check if this is a Renewal Auto template
        if self.order_id.sale_order_template_id and self.order_id.sale_order_template_id.name == "Renewal Auto":
            # Get the renewal products from the order
            renewal_products = self.order_id.renewal_product_items
            
            # Check if this line corresponds to a renewal product
            for renewal_item in renewal_products:
                # Check if the serial number exists in the product name or order line name
                serial_number = renewal_item.name
                if serial_number in (self.product_id.name or '') or serial_number in (self.name or ''):
                    # Search for matching stock.lot with the same serial number and owner
                    matching_lot = self.env['stock.lot'].search([
                        ('name', '=', serial_number),
                        ('owner', '=', self.order_id.partner_id.id)
                    ], limit=1)
                    
                    if matching_lot and matching_lot.product_id:
                        # Use the product from the matching lot for the delivery
                        values['renewal_lot_id'] = matching_lot.id
                        values['renewal_product_id'] = matching_lot.product_id.id
                        break
        
        return values
    
    def _create_procurement(self, product_qty, procurement_uom, values):
        """
        Override to use the correct product from values if it was modified
        for renewal products.
        """
        # If renewal_product_id was set in procurement values (for renewal products)
        if 'renewal_product_id' in values and values['renewal_product_id']:
            product = self.env['product.product'].browse(values['renewal_product_id'])
            
            # Create procurement with the renewal product
            return self.env['procurement.group'].Procurement(
                product, product_qty, procurement_uom, 
                self.order_id.partner_shipping_id.property_stock_customer,
                product.display_name, self.order_id.name, 
                self.order_id.company_id, values
            )
        
        # Otherwise, use the default behavior
        return super(orderLineProquotes, self)._create_procurement(product_qty, procurement_uom, values)
    
    def _prepare_invoice_line(self, **optional_values):
        """
        Override to handle renewal products with serial numbers for invoices.
        For Renewal Auto template, use the correct product from stock.lot if a match is found.
        Also tag the line so we can inject a section above it after invoice creation.
        """
        values = super(orderLineProquotes, self)._prepare_invoice_line(**optional_values)

        # Only for the specific template
        if self.order_id.sale_order_template_id and self.order_id.sale_order_template_id.name == "Renewal Auto":
            renewal_products = self.order_id.renewal_product_items

            for renewal_item in renewal_products:
                serial_number = renewal_item.name or ''
                if serial_number and (serial_number in (self.product_id.name or '') or serial_number in (self.name or '')):
                    matching_lot = self.env['stock.lot'].search([
                        ('name', '=', serial_number),
                        ('owner', '=', self.order_id.partner_id.id)
                    ], limit=1)

                    if matching_lot and matching_lot.product_id:
                        # Use the product from the matching lot for the invoice
                        values['product_id'] = matching_lot.product_id.id

                        # Base name becomes the clean product name
                        clean_name = matching_lot.product_id.name or ''
                        values['name'] = clean_name

                        # ---- NEW: tag the future invoice line & compute section label
                        # Use the first line of the SO line's name as the section header
                        so_header = (self.name or '').splitlines()[0].strip()
                        # Fallback: if empty, still put something useful
                        if not so_header:
                            so_header = clean_name

                        values['x_needs_section'] = True
                        values['x_section_label'] = so_header
                        # ---- /NEW

                        break

        return values

class PreconfigSaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    preconfigured_section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')