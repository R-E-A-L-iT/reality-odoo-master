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
from odoo import models, fields, api, Command

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    variant = fields.Many2one("proquotes.variant", string="Variant Group")

    # applied_name = fields.Char(compute="get_applied_name", string="Applied Name")
    applied_name = fields.Char(string="Applied Name")

    # Per-language section titles: {lang_code: text}. Replaces the old
    # "#translate+EN+FR" name-parsing so one quotation template can serve
    # customers of any language with correct section names. Edited via the
    # "Translate" action in the section dropdown.
    section_name_translations = fields.Json(string="Section Name Translations")

    @api.onchange("name")
    def _proquotes_sync_section_translation(self):
        # Keep the current UI language's entry in sync with inline edits of a
        # section/subsection title, so switching the backend language relabels it
        # and the online/PDF quote can render the customer's language.
        for line in self:
            if line.display_type in ("line_section", "line_subsection"):
                lang = self.env.context.get("lang") or self.env.user.lang or "en_US"
                translations = dict(line.section_name_translations or {})
                if line.name:
                    if translations.get(lang) != line.name:
                        translations[lang] = line.name
                        line.section_name_translations = translations

    def _proquotes_section_name(self, lang=None):
        """Resolve a section's display name for ``lang`` from the stored
        translations, falling back to the raw name. Non-section lines just return
        their name."""
        self.ensure_one()
        lang = lang or self.env.context.get("lang") or self.env.user.lang or "en_US"
        translations = self.section_name_translations or {}
        return translations.get(lang) or self.name or ""

    hiddenSection = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        default="no",
        required=True,
        help="Field To Track if Sections are folded",
    )

    quantityLocked = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Lock Quantity",
        default="yes",
        required=True,
        help="Field to Lock Quantity on Products",
    )

    is_quantityLocked = fields.Boolean(
        string="Lock Quantity",
        compute="_compute_is_quantityLocked",
        inverse="_inverse_is_quantityLocked",
        store=True,
        readonly=False,
        help="Boolean mirror of quantityLocked for the backend order-line form.",
    )

    x_parent_rental_kit_line_id = fields.Many2one(
        "sale.order.line",
        string="Parent Rental Kit Line",
        copy=False,
        index=True,
    )

    x_is_rental_kit_component = fields.Boolean(
        string="Rental Kit Component Line",
        default=False,
        copy=False,
        index=True,
    )

    preconfigured_section_id = fields.Many2one('preconfigured.section', string='Preconfigured Section')

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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        for line in self:
            if line.product_id:
                target_categories = [
                    'Software (Permanent License)',
                    'Software CCP',
                    'Software Subscription'
                ]
                if line.product_id.categ_id and line.product_id.categ_id.name in target_categories:
                    line.price_unit = line.product_id.list_price
                else:
                    line.price_unit = line.product_id.lst_price

    @api.depends('quantityLocked')
    def _compute_is_quantityLocked(self):
        for rec in self:
            rec.is_quantityLocked = rec.quantityLocked == 'yes'

    def _inverse_is_quantityLocked(self):
        for rec in self:
            rec.quantityLocked = 'yes' if rec.is_quantityLocked else 'no'

    def get_sale_order_line_multiline_description_sale(self, product):
        return product.get_product_multiline_description_sale()

    def _proquotes_description_sale_html(self):
        """Product sales description rendered as raw HTML for the quote page.

        `product.description_sale` is a Text field that we intentionally author
        with HTML (``<ul><li>…``) to format the quote line. Odoo 19 removed
        ``t-raw``; ``t-out`` escapes plain strings, so wrap the value in Markup
        here and render it with ``t-out`` in quote_preview.xml.
        """
        from markupsafe import Markup
        self.ensure_one()
        return Markup(self.product_id.description_sale or "")

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_ids')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.

        Odoo 19 reworked the tax API: account.tax._compute_taxes() +
        line._convert_to_tax_base_line_dict() were replaced by per-base-line
        computation (_prepare_base_line_for_taxes_computation /
        _add_tax_details_in_base_line / _round_base_lines_tax_details) reading
        the amounts off base_line['tax_details']. Zero-qty lines keep
        contributing 0 to the untaxed subtotal (original behavior).
        """
        AccountTax = self.env['account.tax']
        for line in self:
            company = line.company_id or self.env.company
            base_line = line._prepare_base_line_for_taxes_computation()
            AccountTax._add_tax_details_in_base_line(base_line, company)
            AccountTax._round_base_lines_tax_details([base_line], company)
            computed_untaxed = base_line['tax_details']['total_excluded_currency']
            computed_total = base_line['tax_details']['total_included_currency']
            amount_tax = computed_total - computed_untaxed

            if line.product_uom_qty == 0:
                amount_untaxed = 0.00
            else:
                amount_untaxed = computed_untaxed

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
        values = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        
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
        return super(SaleOrderLine, self)._create_procurement(product_qty, procurement_uom, values)
    
    def _prepare_invoice_line(self, **optional_values):
        """
        Override to handle renewal products with serial numbers for invoices.
        For Renewal Auto template, use the correct product from stock.lot if a match is found.
        Also tag the line so we can inject a section above it after invoice creation.
        """
        values = super(SaleOrderLine, self)._prepare_invoice_line(**optional_values)

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

    # tax automation methods
    def _orders_to_retax(self):
        return self.mapped("order_id").filtered(lambda order: order.exists())


    @api.onchange("product_id", "product_uom_qty", "price_unit", "discount")
    def _onchange_apply_canadian_sales_taxes_from_line(self):
        for line in self:
            if line.order_id:
                line.order_id._apply_canadian_sales_taxes()


    @api.model_create_multi
    def create(self, vals_list):
        # Trace EVERY sale.order.line creation so we can see exactly when and
        # how Odoo adds spurious lines during rental pickup/return.
        for vals in vals_list:
            _logger.info(
                "[KIT-CLEANUP] SaleOrderLine.create — order_id=%s  product_id=%s  "
                "x_is_rental_kit_component=%s  "
                "context={skip_procurement:%s  tracking_disable:%s  suppress_extra_line_chatter:%s}",
                vals.get('order_id'),
                vals.get('product_id'),
                vals.get('x_is_rental_kit_component'),
                self.env.context.get('skip_procurement'),
                self.env.context.get('tracking_disable'),
                self.env.context.get('suppress_extra_line_chatter'),
            )

        # When sale_renting._action_done adds retroactive lines after a transfer is validated,
        # it passes skip_procurement=True.  We intercept here to block duplicate creation for
        # any product that already has a kit-component line on the order.
        #
        # NOTE: move_ids may or may not be present in the vals — do NOT gate on its presence.
        # The check is purely: does this product already have a line on the order?
        if self.env.context.get("skip_procurement"):
            allowed = []
            for vals in vals_list:
                order_id = vals.get("order_id")
                product_id = vals.get("product_id")

                if order_id and product_id:
                    order = self.env["sale.order"].browse(order_id)

                    # Block only when a kit-component line for this product already exists.
                    # This lets _ensure_rental_kit_component_lines create the line the
                    # first time (kit_comp is empty then), while blocking any subsequent
                    # attempt by sale_renting to add a duplicate "extra line" for the
                    # same product once our component line is in place.
                    kit_comp = order.order_line.filtered(
                        lambda l: l.product_id.id == product_id
                            and not l.display_type
                            and l.x_is_rental_kit_component
                    )

                    if kit_comp:
                        # Redirect any moves that came with this val to the existing line.
                        move_ids = self._extract_move_ids_from_commands(vals.get("move_ids"))
                        if move_ids:
                            self.env["stock.move"].browse(move_ids).write(
                                {"sale_line_id": kit_comp[0].id}
                            )
                        _logger.info(
                            "Blocked retro SOL for order %s product_id=%s — "
                            "redirected to existing kit-component line %s",
                            order.display_name, product_id, kit_comp[0].id,
                        )
                        continue  # skip — do not allow this line to be created

                allowed.append(vals)

            created = self.browse()
            if allowed:
                created |= super().create(allowed)
            created._orders_to_retax()._apply_canadian_sales_taxes()
            return created

        lines = super().create(vals_list)
        lines._orders_to_retax()._apply_canadian_sales_taxes()
        return lines


    def write(self, vals):
        orders_before = self._orders_to_retax()

        res = super().write(vals)

        if self.env.context.get("skip_apply_canadian_sales_taxes"):
            return res

        trigger_fields = {
            "product_id",
            "product_uom_qty",
            "price_unit",
            "discount",
            "display_type",
            "order_id",
        }

        if trigger_fields & set(vals.keys()):
            (orders_before | self._orders_to_retax())._apply_canadian_sales_taxes()

        return res


    def unlink(self):
        orders = self._orders_to_retax()
        res = super().unlink()
        orders._apply_canadian_sales_taxes()
        return res