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

class SaleOrderLine(models.Model):
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

    def _extract_move_ids_from_commands(self, cmds):
        ids = []
        if not cmds:
            return ids
        for c in cmds:
            if isinstance(c, (list, tuple)) and len(c) >= 2 and c[0] == 4:
                ids.append(c[1])
            elif isinstance(c, Command) and getattr(c, "command", None) == 4:
                ids.append(c.id)
        return ids

    # if line is being created retroactively by stock.picking (delivery), override creation
    def create(self, vals_list):
        
        ctx = self.env.context
        if not ctx.get("skip_procurement"):
            return super().create(vals_list)

        allowed = []
        for vals in vals_list:
            move_ids = self._extract_move_ids_from_commands(vals.get("move_ids"))
            if not move_ids:
                allowed.append(vals)
                continue

            order = self.env["sale.order"].browse(vals.get("order_id"))
            product = self.env["product.product"].browse(vals.get("product_id"))
            moves = self.env["stock.move"].browse(move_ids)

            existing = order.order_line.filtered(lambda l: l.product_id.id == product.id)
            if existing:
                moves.write({"sale_line_id": existing[0].id})
            else:
                moves.write({"sale_line_id": False})

            _logger.info(
                "Blocked retro SO line creation for %s (product %s) from moves %s",
                order.display_name, product.display_name, moves.ids
            )

        created = self.browse()
        if allowed:
            created |= super(SaleOrderLine, self).create(allowed)
        return created

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

    preconfigured_section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')

    def _get_pricelist_price(self):
        self.ensure_one()
        if self.is_rental and not self.product_id.product_tmpl_id.default_rental_behaviour:
            product = self.product_id.product_tmpl_id
            start_date = self.start_date
            return_date = self.return_date
            if not (start_date and return_date):
                return 0.0

            daily_rate = product.rental_base
            duration_days = (return_date - start_date).days

            if duration_days <= 4:
                price = daily_rate * duration_days
            elif duration_days <= 7:
                price = daily_rate * 4
            elif duration_days <= 11:
                price = daily_rate * 4 + daily_rate * (duration_days - 7)
            elif duration_days <= 30:
                price = daily_rate * 12
            else:
                remaining_days = duration_days - 30
                price = daily_rate * 12
                if remaining_days <= 7:
                    price += min(remaining_days, 4) * daily_rate if remaining_days <= 4 else 4 * daily_rate
                else:
                    full_weeks = remaining_days // 7
                    extra_days = remaining_days % 7
                    price += full_weeks * 4 * daily_rate + extra_days * daily_rate

            return price

        # Fallback to standard behavior
        return super()._get_pricelist_price()

    @api.onchange('start_date', 'return_date')
    def _onchange_rental_dates(self):
        if self.is_rental:
            self.price_unit = self._get_pricelist_price()

    
    # this checks if the product name has parantheses in it, and if so, can the contents be used to find a matching stock.lot record
    # if so, it adds the product template of the product the stock.lot is for, not the original product (which is for display purposes)
    def _prepare_invoice_line(self, **optional_values):
        vals = super()._prepare_invoice_line(**optional_values)

        if self.display_type:
            return vals

        line_text = (self.name or self.product_id.display_name or "")

        groups = re.findall(r'\(([^()]*)\)', line_text)
        if not groups:
            _logger.info('No parentheses found in line text: %s', line_text)
            return vals

        token = groups[-1].strip()
        if not token:
            _logger.info('No serial number found within parentheses in line text: %s', line_text)
            return vals

        owner_partner = self.order_id.partner_id.commercial_partner_id
        lot = self.env['stock.lot'].sudo().search([
            ('name', '=', token),
            ('owner', '=', owner_partner.id),
        ], limit=1)

        if lot and lot.product_id:
            _logger.info('Matching stock.lot found for token: %s, using product: %s', token, lot.product_id.display_name)
            vals['product_id'] = lot.product_id.id
        else:
            _logger.info('No matching stock.lot found for token: %s', token)

        return vals

    # tax applying code
    @api.onchange("product_id", "product_uom_qty")
    def _onchange_line_reapply_province_taxes(self):
        # Delegate to the order to keep logic in one place
        if self.order_id:
            self.order_id._apply_canadian_province_taxes()

    def write(self, vals):
        res = super().write(vals)
        # If product or qty changed, re-apply
        if {"product_id", "product_uom_qty"} & set(vals.keys()):
            for line in self:
                if line.order_id:
                    line.order_id._apply_canadian_province_taxes()
        return res