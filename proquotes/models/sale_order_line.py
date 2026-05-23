# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo import models, fields, api, Command
from odoo.tools.misc import groupby as tools_groupby


_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    variant = fields.Many2one("proquotes.variant", string="Variant Group")

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
        return product.get_product_multiline_description_sale()

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

    _inherit = 'sale.order.line'

    rental_daily_price = fields.Float(
        compute='_compute_rental_daily_price',
        digits='Product Price',
    )

    @api.depends('order_id.is_rental_order', 'product_id', 'order_id.pricelist_id')
    def _compute_rental_daily_price(self):
        for line in self:
            is_rental_line = line.order_id.is_rental_order and line.product_id.rent_ok
            line.rental_daily_price = line._get_custom_rental_daily_price() if is_rental_line else 0.0

    def _get_pricelist_price(self):
        """Override to apply custom rental pricing formula when enabled on the product."""
        self.ensure_one()

        # Use order-level is_rental_order + product rent_ok instead of line.is_rental.
        # line.is_rental is stored at creation time and requires 'in_rental_app' context,
        # which is absent when lines are added via templates or other non-rental-app paths.
        is_rental_line = self.order_id.is_rental_order and self.product_id.rent_ok

        if is_rental_line and self.product_id.product_tmpl_id.use_custom_rental_price:
            daily_price = self._get_custom_rental_daily_price()
            if not daily_price:
                return super()._get_pricelist_price()
            start_date = self.order_id.rental_start_date
            return_date = self.order_id.rental_return_date

            if start_date and return_date:
                # Minimum rental is 1 day; same-day counts as 1 day.
                days = max(1, (return_date.date() - start_date.date()).days)
                return self._compute_custom_rental_price(daily_price, days)

            return daily_price

        return super()._get_pricelist_price()

    def _get_custom_rental_daily_price(self):
        """Resolve the daily price for the custom rental formula.

        Priority:
          1. Daily rule (unit='day', duration=1) matching the order's pricelist.
          2. Daily rule (unit='day', duration=1) with no pricelist (global rule).
          3. Daily rule whose pricelist has the same currency as the order pricelist.
          4. 0.0 if no daily rule found (template falls back to Odoo's price_unit).
        """
        self.ensure_one()
        tmpl = self.product_id.product_tmpl_id
        order_pricelist = self.order_id.pricelist_id

        daily_rules = tmpl.product_pricing_ids.filtered(
            lambda p: p.recurrence_id.unit == 'day' and p.recurrence_id.duration == 1
        )

        # 1. Match the order's pricelist exactly.
        if order_pricelist:
            matched = daily_rules.filtered(lambda p: p.pricelist_id == order_pricelist)
            if matched:
                return matched[0].price

        # 2. Global daily rule (no pricelist).
        global_rule = daily_rules.filtered(lambda p: not p.pricelist_id)
        if global_rule:
            return global_rule[0].price

        # 3. Daily rule whose pricelist shares the same currency as the order pricelist.
        #    Handles the case where the order uses a general pricelist in the same currency
        #    as a rental-specific pricelist (e.g. order uses "CAD" → matches "CAD RENTAL (CAD)").
        if order_pricelist and daily_rules:
            currency_match = daily_rules.filtered(
                lambda p: p.pricelist_id and p.pricelist_id.currency_id == order_pricelist.currency_id
            )
            if currency_match:
                return currency_match[0].price

        # 4. No daily pricing rule found — return 0 so the template falls back to
        #    Odoo's computed price_unit (the proper rental price, not the sale price).
        return 0.0

    @staticmethod
    def _compute_custom_rental_price(daily_price, days):
        if days <= 0:
            return 0

        def paid_days_for_partial_month(day_count):
            full_weeks = day_count // 7
            extra_days = day_count % 7
            return min((full_weeks * 4) + min(extra_days, 4), 12)

        full_months = days // 30
        remaining_days = days % 30

        paid_days = full_months * 12

        if remaining_days:
            paid_days += paid_days_for_partial_month(remaining_days)

        return daily_price * paid_days

    def _partition_so_lines_by_rental_period(self):
        """Override to guard against False reservation_begin / return_date.

        When rental dates are left empty (allowed by our proquotes customisation),
        base Odoo tries max(False, now) which raises TypeError.  Fall back to
        `now` for any missing date so the groupby still runs cleanly.
        """
        now = fields.Datetime.now()
        lines_grouping_key = {
            line.id: (line.reservation_begin or now, line.return_date or now, line.order_id.warehouse_id.id)
            for line in self
        }
        keyfunc = lambda line_id: (
            max(lines_grouping_key[line_id][0], now),
            lines_grouping_key[line_id][1],
            lines_grouping_key[line_id][2],
        )
        return tools_groupby(self._ids, key=keyfunc)
