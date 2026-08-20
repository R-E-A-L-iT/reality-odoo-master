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

    # ── Single-choice sections ──────────────────────────────────────────────
    # A "single choice" section is one where exactly one of its products may be
    # selected (qty >= 1) at a time; the rest are forced to qty 0. It is an
    # independent, self-contained mode (mutually exclusive with the native
    # "optional" section feature). x_single_choice is set on the SECTION line.
    x_single_choice = fields.Boolean(
        string="Single Choice Section",
        default=False,
        copy=True,
        help="When set on a section, the customer may select only one of its "
             "products (the others are forced to quantity 0).",
    )

    # Each member product line stores an explicit link to its section. Membership
    # is a STORED link (not derived at runtime from the native, non-stored
    # ``parent_id``) so the exclusivity cascade in write() is reliable and fast
    # even from the isolated portal quantity-change path.
    x_single_choice_section_id = fields.Many2one(
        "sale.order.line",
        string="Single Choice Section Line",
        copy=False,
        index=True,
        ondelete="set null",
        help="Product line's single-choice section (set when the section is made "
             "single choice).",
    )

    x_single_choice_member = fields.Boolean(
        string="Single Choice Member",
        compute="_compute_x_single_choice_member",
        store=True,
        help="Product line that belongs to a single-choice section.",
    )

    @api.depends("x_single_choice_section_id")
    def _compute_x_single_choice_member(self):
        for line in self:
            line.x_single_choice_member = bool(line.x_single_choice_section_id)

    # ── Optional sections (checkbox multi-select) ───────────────────────────
    # An "optional" section (native ``is_optional`` on the section line) lets the
    # customer tick any number of its products on/off. Selection-ness is NOT a
    # stored flag: a member is "selected" iff its real ``product_uom_qty`` >= 1
    # (so unselected lines stay at qty 0 and never hit totals/invoices). Each
    # member also carries a hidden "preset" quantity — the qty it takes when the
    # customer selects it — shown (greyed) on unselected rows so they can see what
    # they'd get. Mirrors the single-choice tagging so the portal + backend can
    # tell a member from an ordinary line cheaply.
    x_preset_qty = fields.Float(
        string="Preset Quantity",
        default=1.0,
        copy=True,
        digits="Product Unit of Measure",
        help="For a product in an optional section: the quantity the line takes "
             "when the customer selects it (shown, greyed, while unselected). Not "
             "editable by the customer.",
    )

    x_optional_section_id = fields.Many2one(
        "sale.order.line",
        string="Optional Section Line",
        copy=False,
        index=True,
        ondelete="set null",
        help="Product line's optional section (set when the section is made "
             "optional).",
    )

    x_optional_member = fields.Boolean(
        string="Optional Member",
        compute="_compute_x_optional_member",
        store=True,
        help="Product line that belongs to an optional section.",
    )

    @api.depends("x_optional_section_id")
    def _compute_x_optional_member(self):
        for line in self:
            line.x_optional_member = bool(line.x_optional_section_id)

    def _single_choice_member_lines(self):
        """Product lines belonging to this section, in document order — stopping at
        the next section of the same or higher level (subsections nested inside a
        section are included)."""
        self.ensure_one()
        lines = self.order_id.order_line.sorted(lambda l: (l.sequence, l.id))
        is_subsection = self.display_type == "line_subsection"
        members = self.env["sale.order.line"]
        collecting = False
        for line in lines:
            if line == self:
                collecting = True
                continue
            if not collecting:
                continue
            if line.display_type == "line_section":
                break
            if line.display_type == "line_subsection":
                if is_subsection:
                    break
                continue
            if line.display_type:  # note
                continue
            members |= line
        return members

    def _single_choice_siblings(self):
        """Other product lines that belong to the same single-choice section.

        Derived from the section's members by document order (not by matching the
        stored section link on every sibling), so a single missing/stale tag never
        prevents the exclusivity cascade from zeroing the previous selection."""
        self.ensure_one()
        section = self.x_single_choice_section_id
        if not section:
            return self.env["sale.order.line"]
        return section._single_choice_member_lines() - self

    def portal_select_single_choice(self):
        """Portal selection: make this product the chosen one in its single-choice
        section (qty >= 1) and force every other member to 0. Deterministic, so the
        online quote doesn't depend on the generic quantity-change cascade."""
        self.ensure_one()
        section = self.x_single_choice_section_id
        if not section:
            return False
        others = section._single_choice_member_lines() - self
        others.with_context(_single_choice_no_cascade=True).write(
            {"product_uom_qty": 0}
        )
        if self.product_uom_qty < 1:
            self.with_context(_single_choice_no_cascade=True).write(
                {"product_uom_qty": 1}
            )
        return True

    def action_make_single_choice(self):
        """Turn a section into a single-choice section: tag its member product
        lines and auto-select the first (qty 1, all others 0)."""
        self.ensure_one()
        if self.display_type not in ("line_section", "line_subsection"):
            return False
        # Single-choice and the native "optional" mode are mutually exclusive
        # (the dropdown greys this item out for optional sections; this is the
        # server-side backstop).
        if self.is_optional:
            return False
        self.x_single_choice = True
        members = self._single_choice_member_lines()
        for idx, line in enumerate(members):
            line.with_context(_single_choice_no_cascade=True).write(
                {
                    "x_single_choice_section_id": self.id,
                    "product_uom_qty": 1 if idx == 0 else 0,
                }
            )
        return True

    def _clear_single_choice(self):
        """Turn off single-choice on this section and untag its members (quantities
        are left untouched)."""
        self.ensure_one()
        self.x_single_choice = False
        members = self.order_id.order_line.filtered(
            lambda l: l.x_single_choice_section_id == self
        )
        members.with_context(_single_choice_no_cascade=True).write(
            {"x_single_choice_section_id": False}
        )

    def action_unset_single_choice(self):
        """Revert a single-choice section back to a normal section."""
        self.ensure_one()
        self._clear_single_choice()
        return True

    def _make_optional_members(self):
        """Tag this (now-optional) section's product lines: link them to the
        section, capture their current qty as the preset (min 1), and drop the real
        qty to 0 so every member starts unselected (matching native optional).
        Idempotent — re-running only re-links, it won't clobber a preset already
        set to a sensible value below the current qty."""
        self.ensure_one()
        for line in self._single_choice_member_lines():
            line.with_context(_single_choice_no_cascade=True).write(
                {
                    "x_optional_section_id": self.id,
                    "x_preset_qty": max(line.product_uom_qty, 1),
                    "product_uom_qty": 0,
                }
            )

    def _clear_optional_members(self):
        """Untag an (no-longer-optional) section's members. Quantities/presets are
        left as-is."""
        self.ensure_one()
        members = self.order_id.order_line.filtered(
            lambda l: l.x_optional_section_id == self
        )
        members.with_context(_single_choice_no_cascade=True).write(
            {"x_optional_section_id": False}
        )

    def portal_toggle_optional(self, select):
        """Portal select/unselect of an optional-section product: selecting sets the
        real qty to the preset (min 1); unselecting drops it to 0. Deterministic, so
        the online quote doesn't depend on the generic quantity-change path."""
        self.ensure_one()
        if not self.x_optional_section_id:
            return False
        qty = max(self.x_preset_qty, 1) if select else 0
        self.with_context(_single_choice_no_cascade=True).write(
            {"product_uom_qty": qty}
        )
        return True

    def action_make_optional(self):
        """Mark a section OR subsection optional. Native "Set Optional" is only
        offered on top-level sections, so this backs the custom subsection dropdown
        item. Writing is_optional runs the tagging cascade in write()."""
        self.ensure_one()
        if self.display_type not in ("line_section", "line_subsection"):
            return False
        self.is_optional = True
        return True

    def action_unset_optional(self):
        """Revert an optional section/subsection back to a normal one."""
        self.ensure_one()
        if self.display_type not in ("line_section", "line_subsection"):
            return False
        self.is_optional = False
        return True

    def _enforce_single_choice_exclusivity(self):
        """For each line just set to qty >= 1, drop its section siblings to 0."""
        for line in self:
            if line.x_single_choice_section_id and line.product_uom_qty >= 1:
                siblings = line._single_choice_siblings().filtered(
                    lambda l: l.product_uom_qty != 0
                )
                if siblings:
                    siblings.with_context(_single_choice_no_cascade=True).write(
                        {"product_uom_qty": 0}
                    )

    def _apply_selection_cascade(self, vals):
        """Post-write cascade for the section-selection features (single choice +
        optional). Called from the single write() below, AFTER super().write, and
        skipped under the ``_single_choice_no_cascade`` re-entrancy guard."""
        if self.env.context.get("_single_choice_no_cascade"):
            return
        if "is_optional" in vals:
            for line in self:
                if line.display_type not in ("line_section", "line_subsection"):
                    continue
                if vals.get("is_optional"):
                    # Optional and single-choice are mutually exclusive: turning a
                    # section optional drops any single-choice mode it had, then
                    # tags its members (preset from current qty, real qty -> 0).
                    if line.x_single_choice:
                        line.with_context(
                            _single_choice_no_cascade=True
                        )._clear_single_choice()
                    line.with_context(
                        _single_choice_no_cascade=True
                    )._make_optional_members()
                else:
                    # No longer optional: untag its members.
                    line.with_context(
                        _single_choice_no_cascade=True
                    )._clear_optional_members()
        if "product_uom_qty" in vals:
            self._enforce_single_choice_exclusivity()

    @api.onchange("product_uom_qty")
    def _onchange_single_choice_qty(self):
        # Best-effort live enforcement in the backend form (the write() override
        # is the authoritative path, covering save + portal edits).
        if self.x_single_choice_section_id and self.product_uom_qty >= 1:
            for sibling in self._single_choice_siblings():
                if sibling.product_uom_qty != 0:
                    sibling.product_uom_qty = 0

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
        # Odoo 19 dropped the group_id parameter from
        # sale.order.line._prepare_procurement_values(self); don't forward it to
        # super (our own optional param is kept for backward-compatible callers).
        values = super(SaleOrderLine, self)._prepare_procurement_values()
        
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

        # ===== REVERT 2026-08-20: rental pickup/return reverted to native Odoo.
        # The block below blocked sale_renting's retroactive "extra line" creation
        # during rental pickup/return (skip_procurement=True) and redirected its moves
        # to our kit-component lines. Commented out so native line/move creation runs.
        # Uncomment to restore.
        # When sale_renting._action_done adds retroactive lines after a transfer is validated,
        # it passes skip_procurement=True.  We intercept here to block duplicate creation for
        # any product that already has a kit-component line on the order.
        #
        # NOTE: move_ids may or may not be present in the vals — do NOT gate on its presence.
        # The check is purely: does this product already have a line on the order?
        # if self.env.context.get("skip_procurement"):
        #     allowed = []
        #     for vals in vals_list:
        #         order_id = vals.get("order_id")
        #         product_id = vals.get("product_id")
        #
        #         if order_id and product_id:
        #             order = self.env["sale.order"].browse(order_id)
        #
        #             # Block only when a kit-component line for this product already exists.
        #             # This lets _ensure_rental_kit_component_lines create the line the
        #             # first time (kit_comp is empty then), while blocking any subsequent
        #             # attempt by sale_renting to add a duplicate "extra line" for the
        #             # same product once our component line is in place.
        #             kit_comp = order.order_line.filtered(
        #                 lambda l: l.product_id.id == product_id
        #                     and not l.display_type
        #                     and l.x_is_rental_kit_component
        #             )
        #
        #             if kit_comp:
        #                 # Redirect any moves that came with this val to the existing line.
        #                 move_ids = self._extract_move_ids_from_commands(vals.get("move_ids"))
        #                 if move_ids:
        #                     self.env["stock.move"].browse(move_ids).write(
        #                         {"sale_line_id": kit_comp[0].id}
        #                     )
        #                 _logger.info(
        #                     "Blocked retro SOL for order %s product_id=%s — "
        #                     "redirected to existing kit-component line %s",
        #                     order.display_name, product_id, kit_comp[0].id,
        #                 )
        #                 continue  # skip — do not allow this line to be created
        #
        #         allowed.append(vals)
        #
        #     created = self.browse()
        #     if allowed:
        #         created |= super().create(allowed)
        #     created._orders_to_retax()._apply_canadian_sales_taxes()
        #     return created

        lines = super().create(vals_list)
        lines._orders_to_retax()._apply_canadian_sales_taxes()
        return lines


    def write(self, vals):
        orders_before = self._orders_to_retax()

        res = super().write(vals)

        # Section-selection cascade (single choice + optional). Runs regardless of
        # the tax-skip context below so selection state stays consistent.
        self._apply_selection_cascade(vals)

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