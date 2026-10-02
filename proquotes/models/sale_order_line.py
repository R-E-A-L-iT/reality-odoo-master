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

# Serials sale_stock_renting stores on a rental line. A stored compute
# loads them as superuser, so the shared cache can hold a lot the user
# cannot read. The next read of that lot raises the multi-company rule.
_RENTAL_LOT_FIELDS = (
    "reserved_lot_ids",
    "pickedup_lot_ids",
    "returned_lot_ids",
    "unavailable_lot_ids",
)


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

    # The database column is NOT NULL (required=True). default=False lets
    # every create path that does not pass these keys still insert a value:
    # the down payment wizard, sale_stock/rental extra lines, delivery and
    # website cart lines. Without it those creates fail with "a mandatory
    # field is not set". The backend form always sends them, so it is
    # unaffected.
    is_optional = fields.Boolean(
        required=True, default=False, string="Optional",
        help="Field to Mark Product as Optional",
    )
    is_selected = fields.Boolean(
        required=True, default=False, string="Selected",
        help="Field to Mark Wether Customer has Selected Product",
    )
    is_quantityLocked = fields.Boolean(
        string="Lock Quantity",
        required=True,
        default=False,
        help="Field to Lock Quantity on Products",
    )

    demo_selected = fields.Boolean(string="Selected", compute="_check_selected_line",
                                   help="Field to Mark Wether Customer has Selected Product",
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
            # Do not force is_selected off here. A quotation template sets
            # selected, and the checkbox is filled from that string. Forcing
            # False left the Selected box off, and the next checkbox onchange
            # then rewrote selected from that default.
            template = line.order_id.sale_order_template_id
            if template and (template.name or '').lower() == 'sales blank':
                line.is_selected = True
                
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

    def _proquotes_align_selection_flags(self, vals):
        """Copy string flags onto booleans, or the other way, on a real write.

        The form checkbox edits the booleans and the portal edits ``selected``.
        This keeps one write from leaving them apart. It must not run from a
        compute: reading the form used to save the line and recompute totals.
        """
        vals = dict(vals)
        if 'selected' in vals and 'is_selected' not in vals:
            vals['is_selected'] = vals['selected'] == 'true'
        elif 'is_selected' in vals and 'selected' not in vals:
            vals['selected'] = 'true' if vals['is_selected'] else 'false'
        if 'optional' in vals and 'is_optional' not in vals:
            vals['is_optional'] = vals['optional'] == 'yes'
        elif 'is_optional' in vals and 'optional' not in vals:
            vals['optional'] = 'yes' if vals['is_optional'] else 'no'
        if 'quantityLocked' in vals and 'is_quantityLocked' not in vals:
            vals['is_quantityLocked'] = vals['quantityLocked'] == 'yes'
        elif 'is_quantityLocked' in vals and 'quantityLocked' not in vals:
            vals['quantityLocked'] = 'yes' if vals['is_quantityLocked'] else 'no'
        return vals

    @api.depends('selected')
    def _check_selected_line(self):
        """Display helper only. Do not assign stored fields from here."""
        for rec in self:
            rec.demo_selected = rec.selected == 'true'

    def get_sale_order_line_multiline_description_sale(self, product):
        return product.get_product_multiline_description_sale()

    def _proquotes_drop_rental_lot_cache(self):
        """Drop hidden rental serials from the cache, not from the database.

        ``reserved_lot_ids``, ``pickedup_lot_ids`` and ``returned_lot_ids``
        are ordinary many2manys. Reading one applies the lot rule and omits
        serials in an unticked company. A stored compute (line description,
        delivered quantity) runs as superuser and puts every linked serial
        in the shared cache first. The next ``name`` read on that recordset
        is what raises "Stock Production Lot multi-company".

        Only a clean cache entry is rewritten, so a real edit of the serials
        is still flushed. The relation in the database is left alone.
        """
        if not self or self.env.context.get("proquotes_dropping_rental_lots"):
            return
        self = self.with_context(proquotes_dropping_rental_lots=True)
        # compute_sudo keeps the user id and sets su. Search as that user.
        user_lots = self.env(su=False)["stock.lot"]
        dirty = self.env.cache._dirty
        for name in _RENTAL_LOT_FIELDS:
            field = self._fields.get(name)
            if not field:
                continue
            dirty_ids = dirty.get(field, ())
            for line in self:
                if not line.id or line.id in dirty_ids:
                    continue
                if not self.env.cache.contains(line, field):
                    continue
                cached = self.env.cache.get(line, field) or ()
                if not isinstance(cached, (tuple, list)):
                    continue
                cached_ids = tuple(cached)
                if not cached_ids:
                    continue
                visible = user_lots.search([("id", "in", list(cached_ids))])
                visible_ids = tuple(id_ for id_ in cached_ids if id_ in set(visible._ids))
                if visible_ids == cached_ids:
                    continue
                self.env.cache.set(line, field, visible_ids)

    def _compute_name(self):
        # Name is stored, so this compute is superuser and may cache every
        # reserved / picked up / returned serial before the form reads them.
        self._proquotes_drop_rental_lot_cache()
        super()._compute_name()
        self._proquotes_drop_rental_lot_cache()

    def _compute_qty_delivered(self):
        self._proquotes_drop_rental_lot_cache()
        super()._compute_qty_delivered()
        self._proquotes_drop_rental_lot_cache()

    def _get_sale_order_line_multiline_description_sale(self):
        self._proquotes_drop_rental_lot_cache()
        description = super()._get_sale_order_line_multiline_description_sale()
        self._proquotes_drop_rental_lot_cache()
        return description

    def _proquotes_counts_in_totals(self):
        """Whether this line contributes to quote totals.

        Same rule as the tax-totals widget: not a section or note, and the
        customer selected it. sectionSelected is intentionally not part of
        this rule.
        """
        self.ensure_one()
        return not self.display_type and self.selected == 'true'

    @api.depends('product_uom_qty', 'selected', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.

        Unselected optional lines and zero-quantity lines contribute nothing:
        subtotal, tax, and total are all zero. Otherwise the tax engine
        totals are stored unchanged.
        """
        for line in self:
            tax_results = self.env['account.tax'].with_company(line.company_id)._compute_taxes([
                line._convert_to_tax_base_line_dict()
            ])
            totals = list(tax_results['totals'].values())[0]
            if line.selected == 'false' or line.product_uom_qty == 0:
                amount_untaxed = 0.0
                amount_tax = 0.0
            else:
                amount_untaxed = totals['amount_untaxed']
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
        vals_list = [self._proquotes_align_selection_flags(vals) for vals in vals_list]
        # Trace EVERY sale.order.line creation so we can see exactly when and
        # how Odoo adds spurious lines during rental pickup/return.
        for vals in vals_list:
            _logger.info(
                "[KIT-CLEANUP] SaleOrderLine.create — order_id=%s  product_id=%s  "
                "selected=%s  optional=%s  x_is_rental_kit_component=%s  "
                "context={skip_procurement:%s  tracking_disable:%s  suppress_extra_line_chatter:%s}",
                vals.get('order_id'),
                vals.get('product_id'),
                vals.get('selected'),
                vals.get('optional'),
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
        vals = self._proquotes_align_selection_flags(vals)
        orders_before = self._orders_to_retax()
        # Changing the rental end date recomputes the line description and
        # the delivered quantity, both of which read the line's serials.
        rental_dates = {"return_date", "start_date", "reservation_begin"} & set(vals)
        if rental_dates:
            self._proquotes_drop_rental_lot_cache()

        res = super().write(vals)

        if rental_dates:
            self._proquotes_drop_rental_lot_cache()

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