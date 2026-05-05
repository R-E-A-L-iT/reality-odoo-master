# -*- coding: utf-8 -*-

import ast
import base64
import json
from email.policy import default
import re
from math import ceil

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.http import request, route
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

VIEWED_XMLIDS = {'sale.mt_order_viewed', 'sale.mt_quote_viewed'}

VIEWED_XMLIDS = {'sale.mt_order_viewed', 'sale.mt_quote_viewed'}

PROVINCE_TAX_BY_CODE = {
    # code -> tax name in that company's chart
    "QC": "GST + QST for sales",
    "AB": "GST for sales - 5%",
    "BC": "GST + PST for sales (BC)",
    "ON": "HST for sales - 13%",
    "MB": "GST + PST for sales (MB)",
    "NB": "HST for sales - 15%",
    "NL": "HST for sales - 15%",
    "NT": "GST for sales - 5%",
    "NS": "HST 14%",
    "NU": "GST for sales - 5%",
    "PE": "HST for sales - 15%",
    "SK": "GST + PST for sales (SK)",
    "YT": "GST for sales - 5%",
}

def _code_from_state(state):
    if not state:
        return False
    code = (state.code or "").upper()
    name = (state.display_name or state.name or "").upper()

    # 1) trust code if it matches a known one
    if code in PROVINCE_TAX_BY_CODE:
        return code

    # 2) fuzzy name contains, matching your original behavior
    contains = lambda s: s in name
    if contains("QUEBEC") or contains("QUÉBEC"): return "QC"
    if contains("ALBERTA"): return "AB"
    if contains("BRITISH"): return "BC"
    if contains("ONTARIO"): return "ON"
    if contains("MANITOBA"): return "MB"
    if contains("BRUNSWICK"): return "NB"
    if contains("NEWFOUNDLAND"): return "NL"
    if contains("NORTHWEST"): return "NT"
    if contains("SCOTIA"): return "NS"
    if contains("NUNAVUT"): return "NU"
    if contains("PRINCE"): return "PE"
    if contains("SASKATCHEWAN"): return "SK"
    if contains("YUKON"): return "YT"
    return False

class order(models.Model):
    _inherit = "sale.order"

    # Allow same-datetime start/end so same-day (hourly) rentals save without error.
    # Replaces the base sale_renting CHECK(rental_start_date < rental_return_date).
    _sql_constraints = [(
        'rental_period_coherence',
        "CHECK(rental_start_date IS NULL OR rental_return_date IS NULL OR rental_start_date <= rental_return_date)",
        "The rental start date must be before or equal to the rental return date.",
    )]

    partner_id = fields.Many2one(
        'res.partner', 
        string="Customer",
        domain="[('is_company', '=', True)]",
        required=True
    )

    pricelist_id = fields.Many2one(
        'product.pricelist',
        string='Pricelist',
        domain="[('name', 'not ilike', 'Default')]",
        required=True
    )

    approve_financing = fields.Boolean(string="APPROVE Financing")

    # partner_ids = fields.Many2many("res.partner", "display_name", string="Contacts")
    email_contacts = fields.Many2many("res.partner", "display_name", string="Email Contacts")

    products = fields.One2many(related="partner_id.products", readonly=True)

    customer_po_number = fields.Char(string="PO Number")

    company_name = fields.Char(
        related="company_id.name", string="company_name", required=True
    )
    manual_invoice_status = fields.Selection([
        ("full_invoice", "Fully Invoiced"),
        ("partially_invoiced", "Partially Invoiced"),
        ("not_invoiced", "Not Invoiced"),
    ], )
    partner_name = fields.Char(string="Partner Name")
    rental_email = fields.Char(string="Email")

    def _get_quote_mail_template(self):
        """Pick the template to preselect in the Send Quote wizard."""
        self.ensure_one()

        # If you want the priority exactly as you wrote:
        # rental > renewal > general
        if self.is_rental:
            name = "Rental Contract"
        elif self.is_renewal:
            name = "Renewal"
        else:
            name = "General Sales"

        tmpl = self.env["mail.template"].search([("name", "=", name)], limit=1)
        if not tmpl:
            _logger.warning("Quote email template not found by name: %s", name)
        return tmpl



    # 
    # 
    # TAXES AUTOMATIONS
    # 
    # 

    def _is_ca_company_scope(self):
        """Limit to your Canadian company, same condition as your rule."""
        # Keep your business rule as-is:
        return self.company_id and self.company_id.name == "R-E-A-L.iT Solutions"

    def _get_province_tax(self, province_code):
        """Return the account.tax record for the province under the order's company."""
        self.ensure_one()
        if not (province_code and self._is_ca_company_scope()):
            return self.env["account.tax"]
        tax_name = PROVINCE_TAX_BY_CODE.get(province_code)
        if not tax_name:
            return self.env["account.tax"]
        # Search inside the order's company context
        return (
            self.env["account.tax"]
            .with_company(self.company_id)
            .search([("name", "=", tax_name)], limit=1)
        )

    def _apply_canadian_province_taxes(self):
        """Clear and apply taxes to order lines based on shipping province."""
        for order in self:
            # Only run for your Canadian company and when a shipping state exists
            state = order.partner_shipping_id.state_id
            if not order._is_ca_company_scope() or not state:
                # Clear taxes if we’re not in scope (so you don't accidentally retain old taxes)
                for line in order.order_line:
                    if not line.display_type and line.product_id:
                        line.tax_id = [Command.clear()]
                continue

            province_code = _code_from_state(state)
            province_tax = order._get_province_tax(province_code)

            for line in order.order_line:
                # skip sections/notes and empty lines
                if line.display_type or not line.product_id or line.product_uom_qty <= 0:
                    continue
                if province_tax:
                    # Clear-and-set (ensures nothing else sticks)
                    line.tax_id = [Command.set(province_tax.ids)]
                else:
                    # No match: clear taxes to avoid stale values
                    line.tax_id = [Command.clear()]

    # ---------- Triggers to (re)apply ----------
    @api.onchange("partner_id", "partner_shipping_id", "company_id", "pricelist_id", "sale_order_template_id")
    def _onchange_reapply_province_taxes(self):
        self._apply_canadian_province_taxes()

    def write(self, vals):
        res = super().write(vals)
        # If any of these change, recompute taxes
        if {"partner_id", "partner_shipping_id", "company_id", "pricelist_id"} & set(vals.keys()):
            self._apply_canadian_province_taxes()
        return res


    # 
    # 
    # 
    # 
    # 









    # 
    # 
    # TAXES AUTOMATIONS
    # 
    # 

    def _is_ca_company_scope(self):
        """Limit to your Canadian company, same condition as your rule."""
        # Keep your business rule as-is:
        return self.company_id and self.company_id.name == "R-E-A-L.iT Solutions"

    def _get_province_tax(self, province_code):
        """Return the account.tax record for the province under the order's company."""
        self.ensure_one()
        if not (province_code and self._is_ca_company_scope()):
            return self.env["account.tax"]
        tax_name = PROVINCE_TAX_BY_CODE.get(province_code)
        if not tax_name:
            return self.env["account.tax"]
        # Search inside the order's company context
        return (
            self.env["account.tax"]
            .with_company(self.company_id)
            .search([("name", "=", tax_name)], limit=1)
        )

    def _apply_canadian_province_taxes(self):
        """Clear and apply taxes to order lines based on shipping province."""
        for order in self:
            # Only run for your Canadian company and when a shipping state exists
            state = order.partner_shipping_id.state_id
            if not order._is_ca_company_scope() or not state:
                # Clear taxes if we’re not in scope (so you don't accidentally retain old taxes)
                for line in order.order_line:
                    if not line.display_type and line.product_id:
                        line.tax_id = [Command.clear()]
                continue

            province_code = _code_from_state(state)
            province_tax = order._get_province_tax(province_code)

            for line in order.order_line:
                # skip sections/notes and empty lines
                if line.display_type or not line.product_id or line.product_uom_qty <= 0:
                    continue
                if province_tax:
                    # Clear-and-set (ensures nothing else sticks)
                    line.tax_id = [Command.set(province_tax.ids)]
                else:
                    # No match: clear taxes to avoid stale values
                    line.tax_id = [Command.clear()]

    # ---------- Triggers to (re)apply ----------
    @api.onchange("partner_id", "partner_shipping_id", "company_id", "pricelist_id", "sale_order_template_id")
    def _onchange_reapply_province_taxes(self):
        self._apply_canadian_province_taxes()

    def write(self, vals):
        res = super().write(vals)
        # If any of these change, recompute taxes
        if {"partner_id", "partner_shipping_id", "company_id", "pricelist_id"} & set(vals.keys()):
            self._apply_canadian_province_taxes()
        return res


    # 
    # 
    # 
    # 
    # 



    @api.model
    def _is_viewed_post(self, kwargs):
        # Default path sometimes passes subtype via xmlid, sometimes via id
        subtype_xmlid = kwargs.get('subtype_xmlid')
        if subtype_xmlid in VIEWED_XMLIDS:
            return True
        subtype_id = kwargs.get('subtype_id')
        if subtype_id:
            try:
                rec = self.env['mail.message.subtype'].browse(subtype_id)
                if rec and rec.get_external_id().get(rec.id) in VIEWED_XMLIDS:
                    return True
            except Exception:
                pass
        # Fallback: body starts with generic text (covers localized builds poorly; keep xmlids above as primary)
        body = (kwargs.get('body') or '').strip()
        return body.startswith('Quotation viewed by customer')

    # Skip default quote viewed messages when user_id is NOT present in URL
    # This ensures only tracking URLs (with user_id) trigger notifications
    def message_post(self, **kwargs):
        try:
            has_user_id = bool(request and request.params.get('user_id'))
        except Exception:
            has_user_id = False

        # Skip "quote viewed" messages when there's NO user_id in URL (direct access)
        if not has_user_id and self._is_viewed_post(kwargs):
            _logger.info(f"BLOCKING DEFAULT NOTIFICATION: Quote {self.name} - no user_id in URL, skipping default 'viewed' message")
            return self.env['mail.message']

        return super().message_post(**kwargs)

    def message_post_with_view(self, view, **kwargs):
        try:
            has_user_id = bool(request and request.params.get('user_id'))
        except Exception:
            has_user_id = False

        # Skip "quote viewed" messages when there's NO user_id in URL (direct access)
        if not has_user_id and self._is_viewed_post(kwargs):
            _logger.info(f"BLOCKING DEFAULT NOTIFICATION (with_view): Quote {self.name} - no user_id in URL, skipping default 'viewed' message")
            return self.env['mail.message']
        return super().message_post_with_view(view, **kwargs)

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id_set_header_footer(self):
        if self.sale_order_template_id and self.sale_order_template_id.header_id:
            self.header_id = self.sale_order_template_id.header_id
    
    # this function returns a json of the selected items on the quote for the approve plugin
    def get_approve_items_json(self):
        self.ensure_one()
        items = []

        selected_lines = self.order_line.filtered(lambda l: l.is_selected and not l.display_type)

        for line in selected_lines:
            items.append({
                "model": line.product_id.name,
                "price": line.price_unit,
                "quantity": line.product_uom_qty,
                "type": "new_product"
            })

        return json.dumps(items)

    def write(self, vals):
        # Normal write first
        res = super().write(vals)

        # Avoid recursion when we fix things ourselves
        if self.env.context.get('skip_company_consistency'):
            return res

        for order in self:
            # Only enforce this for website orders with a company
            if not order.website_id or not order.company_id:
                continue

            company = order.company_id

            # --- Fix warehouse if mismatched ---
            if order.warehouse_id and order.warehouse_id.company_id != company:
                _logger.info(
                    ">>>>>>> Fixing warehouse company mismatch on %s: SO company=%s, warehouse=%s (%s)",
                    order.name,
                    company.name,
                    order.warehouse_id.display_name,
                    order.warehouse_id.company_id.name,
                )

                warehouse_env = (
                    self.env['stock.warehouse']
                    .sudo()
                    .with_context(allowed_company_ids=[company.id])
                    .with_company(company.id)
                )

                new_wh = warehouse_env.search(
                    [('company_id', '=', company.id)],
                    limit=1,
                )

                if new_wh:
                    _logger.info(
                        ">>>>>>> Assigning warehouse %s to SO %s for company %s",
                        new_wh.display_name,
                        order.name,
                        company.name,
                    )
                    order.with_context(skip_company_consistency=True).write({
                        'warehouse_id': new_wh.id,
                    })
                else:
                    _logger.warning(
                        ">>>>>>> No warehouse found for company %s when fixing SO %s",
                        company.name,
                        order.name,
                    )

            # --- Fix partner companies if mismatched ---
            partners = (order.partner_id | order.partner_invoice_id | order.partner_shipping_id)
            for partner in partners:
                if not partner:
                    continue
                if partner.company_id and partner.company_id != company:
                    _logger.info(
                        ">>>>>>> Fixing partner company for %s on SO %s: %s -> %s",
                        partner.display_name,
                        order.name,
                        partner.company_id.name,
                        company.name,
                    )
                    partner.sudo().with_context(
                        allowed_company_ids=[partner.company_id.id, company.id]
                    ).write({'company_id': company.id})

        return res

    def _set_company_based_on_visitor_country(self):
        """Assign company based on pricelist currency first, then visitor's country as fallback."""
        for order in self:
            # Only process website orders
            if not order.website_id:
                continue

            previous_company = order.company_id
            previous_warehouse = order.warehouse_id

            company_to_assign = None

            # PRIORITY 1: Determine company based on pricelist currency
            if order.pricelist_id and order.pricelist_id.currency_id:
                currency_name = order.pricelist_id.currency_id.name

                _logger.info(
                    '>>>>>>>Website order %s - pricelist: %s, currency: %s',
                    order.name, order.pricelist_id.name, currency_name
                )

                if currency_name == 'USD':
                    # USD pricelist → assign to US company
                    company_to_assign = self.env['res.company'].search(
                        [('name', '=', 'R-E-A-L.iT U.S. Inc.')],
                        limit=1,
                    )
                    _logger.info(
                        '>>>>>>>Assigning US company based on USD pricelist to sale order %s >>>: %s',
                        order.name,
                        company_to_assign.name if company_to_assign else None,
                    )
                elif currency_name == 'CAD':
                    # CAD pricelist → assign to Canadian company
                    company_to_assign = self.env['res.company'].search(
                        [('name', '=', 'R-E-A-L.iT Solutions')],
                        limit=1,
                    )
                    _logger.info(
                        '>>>>>>>Assigning Canadian company based on CAD pricelist to sale order %s >>>: %s',
                        order.name,
                        company_to_assign.name if company_to_assign else None,
                    )

            # PRIORITY 2: Fallback to GeoIP if pricelist doesn't determine company
            if not company_to_assign:
                try:
                    if request and hasattr(request, 'env'):
                        visitor = request.env['website.visitor']._get_visitor_from_request()
                        if visitor and visitor.country_id:
                            us_country = self.env.ref('base.us', raise_if_not_found=False)
                            _logger.info(
                                '>>>>>>>Website order %s - visitor country: %s (GeoIP fallback)',
                                order.name, visitor.country_id.name
                            )

                            if us_country and visitor.country_id.id == us_country.id:
                                # US visitor → assign to R-E-A-L.iT U.S. Inc.
                                company_to_assign = self.env['res.company'].search(
                                    [('name', '=', 'R-E-A-L.iT U.S. Inc.')],
                                    limit=1,
                                )
                                _logger.info(
                                    '>>>>>>>Assigning US company via GeoIP fallback to sale order %s >>>: %s',
                                    order.name,
                                    company_to_assign.name if company_to_assign else None,
                                )
                            else:
                                # Non-US visitor → R-E-A-L.iT Solutions
                                company_to_assign = self.env['res.company'].search(
                                    [('name', '=', 'R-E-A-L.iT Solutions')],
                                    limit=1,
                                )
                                _logger.info(
                                    '>>>>>>>Assigning Canadian company via GeoIP fallback to sale order %s >>>: %s',
                                    order.name,
                                    company_to_assign.name if company_to_assign else None,
                                )
                except Exception as e:
                    _logger.warning(
                        '>>>>>>>Could not get visitor from request for order %s: %s',
                        order.name, str(e),
                    )

            # PRIORITY 3: Final fallback - default to Canadian company
            if not company_to_assign:
                company_to_assign = self.env['res.company'].search(
                    [('name', '=', 'R-E-A-L.iT Solutions')],
                    limit=1,
                )
                _logger.info(
                    '>>>>>>>Final fallback to Canadian company for sale order %s >>>: %s',
                    order.name,
                    company_to_assign.name if company_to_assign else None,
                )

            # If nothing to do or already on that company, skip
            if not company_to_assign or order.company_id == company_to_assign:
                continue

            # --- IMPORTANT: pick a warehouse for that company BEFORE writing company_id ---
            warehouse_env = (
                self.env['stock.warehouse']
                .sudo()
                .with_context(allowed_company_ids=[company_to_assign.id])
                .with_company(company_to_assign.id)
            )

            warehouse = warehouse_env.search(
                [('company_id', '=', company_to_assign.id)],
                limit=1,
            )

            if not warehouse:
                _logger.warning(
                    '>>>>>>>No warehouse found for company %s; sale order %s may crash with incompatible companies',
                    company_to_assign.name,
                    order.name,
                )
                # If really no warehouse, we can only try to switch company and hope nothing uses warehouse
                values = {'company_id': company_to_assign.id}
            else:
                _logger.info(
                    '>>>>>>>Assigning warehouse for %s: %s -> %s',
                    order.name,
                    previous_warehouse.display_name if previous_warehouse else None,
                    warehouse.display_name,
                )
                # Write company and warehouse TOGETHER to avoid check_company errors
                values = {
                    'company_id': company_to_assign.id,
                    'warehouse_id': warehouse.id,
                }

            _logger.info(
                '>>>>>>>Changing company on %s: %s -> %s',
                order.name,
                previous_company.name if previous_company else None,
                company_to_assign.name,
            )

            order.write(values)

            # Let Odoo recompute dependent fields
            try:
                order._onchange_company_id()
            except Exception as e:
                _logger.warning(
                    '>>>>>>>Error in _onchange_company_id for order %s: %s',
                    order.name, str(e),
                )

    # this function adds sales@r-e-a-l.it as a follower automatically upon creation so it receives all the relevant emails
    @api.model
    def create(self, vals):
        order = super().create(vals)

        # Assign company based on visitor location for website orders
        order._set_company_based_on_visitor_country()

        # Find or create the partner with email derek@r-e-a-l.it
        sales_email = self.env['res.partner'].search([('id', '=', '58319')], limit=1)
        if sales_email:
            order.message_subscribe(partner_ids=[sales_email.id])

        target_email = sales_email.email_normalized or (sales_email.email or '').strip().lower()
        if not target_email:
            return order

        follower_partners = order.message_follower_ids.mapped('partner_id')
        follower_emails = {
            (p.email_normalized or (p.email or '').strip().lower())
            for p in follower_partners
            if (p.email or p.email_normalized)
        }

        sp_partner = order.user_id.partner_id if order.user_id else False
        salesperson_email = (sp_partner.email_normalized or (sp_partner.email or '').strip().lower()) if sp_partner else ''

        if target_email in follower_emails or target_email == salesperson_email:
            return order

        # Add non-company partners to subscribers (automatic quotes from store)
        partner = order.partner_id
        if partner and not partner.is_company:
            if partner.id not in order.message_partner_ids.ids:
                order.message_subscribe(partner_ids=[partner.id])

        return order


    @api.model
    def default_get(self, fields_list):
        defaults = super(order, self).default_get(fields_list)

        immediate_payment_term = self.env['account.payment.term'].search(
            [('name', '=', 'Immediate Payment')],
            limit=1
        )
        if immediate_payment_term:
            defaults['payment_term_id'] = immediate_payment_term.id

        user_id = defaults.get("user_id") or self.env.uid
        company_id = defaults.get("company_id") or self.env.company.id

        user = self.env["res.users"].browse(user_id)
        company = self.env["res.company"].browse(company_id)

        footer = self._get_user_company_footer(user=user, company=company)
        if not footer:
            footer = self._get_company_default_footer(company=company)
        if not footer:
            footer = self._get_first_available_footer(company=company)
        if footer:
            defaults["footer_id"] = footer.id

        header = self._get_first_available_header(company=company)
        if header:
            defaults["header_id"] = header.id

        return defaults
    
    @api.onchange('pricelist_id')
    def _onchange_pricelist_id(self):
        if self.pricelist_id:
            for line in self.order_line:
                line.tax_id = [(5, 0, 0)]

    def _recompute_prices(self):
        lines_to_recompute = self._get_update_prices_lines()
        lines_to_recompute.invalidate_recordset(['pricelist_item_id'])
        lines_to_recompute._compute_price_unit()
        # Special case: we want to overwrite the existing discount on _recompute_prices call
        # i.e. to make sure the discount is correctly reset
        # if pricelist discount_policy is different than when the price was first computed.
        for lines in lines_to_recompute:
            if not lines.discount:
                lines.discount = 0.0
        lines_to_recompute._compute_discount()
        self.show_update_pricelist = False
    
    # force ecommerce template use instead if quote created from ecommerce order
    def action_quotation_send(self):
        self.ensure_one()

        action = super().action_quotation_send()

        if self.website_id:
            ecommerce_template = self.env['mail.template'].search([
                ('name', '=', 'eCommerce Quote Send')
            ], limit=1)

            if ecommerce_template:
                if action.get('context'):
                    action['context'].update({
                        'default_template_id': ecommerce_template.id,
                        'default_use_template': bool(ecommerce_template.id),
                    })
                else:
                    action['context'] = {
                        'default_template_id': ecommerce_template.id,
                        'default_use_template': bool(ecommerce_template.id),
                    }
                _logger.info(f"Applied eCommerce Quote Send template automatically for {self.name}")

        return action
            
    def _action_confirm(self):

        admin_email = self.env['res.partner'].search([('email', '=', 'admin@r-e-a-l.it')], limit=1)

        if admin_email:
            self.message_subscribe(partner_ids=[admin_email.id])

        selected_lines = self.order_line.sudo().filtered(
            lambda line: line.selected == 'true' and line.product_id.name != 'No CCP')
        selected_lines._action_launch_stock_rule()



    # this overrides the subscribe method to not allow the partner_id to be subscribed, since their company email is not where the quote should go
    # leaves an exception for non-company contacts, to allow quotes created by the store to be sent out
    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        partner_ids = [
            pid for pid in (partner_ids or [])
            if pid not in [
                p.id for p in self.mapped('partner_id')
                if p.is_company
            ]
        ]
        if not partner_ids:
            return
        return super().message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)

    def has_external_followers(self):
        """
        Check if the sale order has external followers (non-internal users).
        Returns True if there are followers who are not internal users.
        """
        self.ensure_one()
        # Get all followers of the current record
        followers = self.message_partner_ids

        # Filter for external followers (partners without internal user access)
        # Internal users have share=False, external users have share=True or no user
        external_followers = followers.filtered(
            lambda p: not p.user_ids or any(user.share for user in p.user_ids)
        )

        return len(external_followers) > 0
    
    def get_translated_term(self, title, lang):
        if "translate" in title:

            terms = title.split("+", 2)

            if terms[0] == "#translate":
                english = terms[1]
                french = terms[2]
                return french if lang == 'fr_CA' else english
        return title
    
    def parse_ccp_label(self, label):
        try:
            if not label.startswith('#ccplabel+'):
                return label
            
            parts = label.split('+')
            # if len(parts) != 4:
            #     return label
            
            product_code = parts[2]
            expiry_date = parts[3]
            product_name = product_code

            new_label = ""

            expiry_date_obj = datetime.strptime(expiry_date, '%Y-%m-%d')
            if self.env.context.get('lang') == 'fr_CA':
                month_name = expiry_date_obj.strftime('%B').capitalize()
                months_fr = {
                    'January': 'janvier', 'February': 'février', 'March': 'mars',
                    'April': 'avril', 'May': 'mai', 'June': 'juin',
                    'July': 'juillet', 'August': 'août', 'September': 'septembre',
                    'October': 'octobre', 'November': 'novembre', 'December': 'décembre'
                }
                month_name = months_fr.get(month_name, month_name)
                formatted_date = f"{expiry_date_obj.day} {month_name} {expiry_date_obj.year}"
            elif self.env.context.get('lang') == 'es_ES':
                month_name = expiry_date_obj.strftime('%B').lower()
                months_es = {
                    'January': 'enero', 'February': 'febrero', 'March': 'marzo',
                    'April': 'abril', 'May': 'mayo', 'June': 'junio',
                    'July': 'julio', 'August': 'agosto', 'September': 'septiembre',
                    'October': 'octubre', 'November': 'noviembre', 'December': 'diciembre'
                }
                month_name = months_es.get(month_name, month_name)
                formatted_date = f"{expiry_date_obj.day} {month_name} {expiry_date_obj.year}"
            else:
                formatted_date = expiry_date_obj.strftime('%d %B, %Y')

            product = self.env['product.product'].search([('name', '=', product_code)], limit=1)
            if product:
                product_name = product.with_context(lang=self.env.context.get('lang', 'en_US')).name

            if self.env.context.get('lang') == 'fr_CA':
                new_label = f"{product_name} ({parts[1]}) - Expiration: {formatted_date}"
            elif self.env.context.get('lang') == 'es_ES':
                new_label = f"{product_name} ({parts[1]}) - Vencimiento: {formatted_date}"
            else:
                new_label = f"{product_name} ({parts[1]}) - Expiration: {formatted_date}"

            return new_label
        except Exception:
            return label

    def _get_available_footer_domain(self):
        return [
            ("active", "=", True),
            ("record_type", "=", "Footer"),
        ]

    def _get_available_header_domain(self):
        return [
            ("active", "=", True),
            ("record_type", "=", "Header"),
        ]

    @api.model
    def _get_first_available_footer(self, company=False):
        domain = self._get_available_footer_domain()
        footers = self.env["header.footer"].search(domain, order="id asc")
        if company:
            company_specific = footers.filtered(
                lambda f: not f.company_ids or company in f.company_ids
            )
            if company_specific:
                return company_specific[0]
        return footers[:1]

    @api.model
    def _get_first_available_header(self, company=False):
        domain = self._get_available_header_domain()
        headers = self.env["header.footer"].search(domain, order="id asc")
        if company:
            company_specific = headers.filtered(
                lambda h: not h.company_ids or company in h.company_ids
            )
            if company_specific:
                return company_specific[0]
        return headers[:1]

    @api.model
    def _get_user_company_footer(self, user=False, company=False):
        user = user or self.env.user
        company = company or self.env.company

        if not user or not company:
            return self.env["header.footer"]

        # New per-company mapping model from the previous change
        line = self.env["res.users.company.footer"].search(
            [
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if line and line.footer_id and line.footer_id.active and line.footer_id.record_type == "Footer":
            return line.footer_id

        return self.env["header.footer"]

    @api.model
    def _get_company_default_footer(self, company=False):
        company = company or self.env.company
        if (
            company
            and company.default_footer_id
            and company.default_footer_id.active
            and company.default_footer_id.record_type == "Footer"
        ):
            return company.default_footer_id
        return self.env["header.footer"]

    @api.model
    def _default_footer_id(self):
        user = self.env.user
        company = self.env.company

        footer = self._get_user_company_footer(user=user, company=company)
        if footer:
            return footer.id

        footer = self._get_company_default_footer(company=company)
        if footer:
            return footer.id

        footer = self._get_first_available_footer(company=company)
        return footer.id if footer else False

    @api.model
    def _default_header_id(self):
        company = self.env.company
        header = self._get_first_available_header(company=company)
        return header.id if header else False

    header_id = fields.Many2one(
        "header.footer",
        string="Header",
        required=True,
        domain="[('active', '=', True), ('record_type', '=', 'Header')]",
        default=_default_header_id,
    )

    footer_id = fields.Many2one(
        "header.footer",
        string="Footer",
        required=True,
        domain="[('active', '=', True), ('record_type', '=', 'Footer')]",
        default=_default_footer_id,
    )

    @api.onchange("user_id", "company_id")
    def _onchange_user_or_company_set_footer_header(self):
        for order in self:
            company = order.company_id or self.env.company
            user = order.user_id or self.env.user

            footer = order._get_user_company_footer(user=user, company=company)
            if not footer:
                footer = order._get_company_default_footer(company=company)
            if not footer:
                footer = order._get_first_available_footer(company=company)
            order.footer_id = footer.id if footer else False

            header = order._get_first_available_header(company=company)
            if header:
                order.header_id = header.id

    is_renewal = fields.Boolean(string="Renewal Quote", default=False)

    renewal_product_items = fields.Many2many(
        string="Renewal Items", comodel_name="stock.lot"
    )


    @api.onchange("sale_order_template_id")
    def set_is_renewal(self):
        if (
                self.sale_order_template_id.name != False
                and "Renewal" in self.sale_order_template_id.name
        ):
            self.is_renewal = True
        else:
            self.is_renewal = False

    def test_action(self, *args):
        _logger.error("HELLO THERE" + str(args[0]))

    def generate_section_line(self, name, *, special="regular", selected="true"):
        section = self.env["sale.order.line"].new(
            {
                "name": name,
                "special": special,
                "display_type": "line_section",
                "order_id": self._origin.id,
                "selected": selected,
            }
        )
        return section

    def generate_product_line(self, product_id, *, selected=False, uom="Units", locked_qty="yes", optional="no"):
        if selected is True:
            selected = "true"
        elif selected is False:
            selected = "false"

        product = self.env["product.product"].browse(product_id.id)

        # Price from pricelist (as you already do)
        pricelist = self.pricelist_id.id
        pricelist_entry = self.env["product.pricelist.item"].search(
            [("pricelist_id.id", "=", pricelist), ("product_tmpl_id.sku", "=", product.sku)]
        )
        if len(pricelist_entry) > 1:
            return "Duplicate Pricelist Rules: " + str(product_id.sku)
        price = pricelist_entry[-1].fixed_price if len(pricelist_entry) == 1 else 0

        # DO NOT set product_uom: Odoo will use product.uom_id & validate categories.
        line_vals = {
            "name": product.name,
            "selected": selected,
            "optional": optional,
            "quantityLocked": locked_qty,
            "product_id": product.id,
            "product_uom_qty": 1,
            "price_unit": price,
            "order_id": self._origin.id,
        }
        return self.env["sale.order.line"].new(line_vals)

    def hardwareCCP(self, hardware_lines, product):
        eid = product.name

        # Generate lines based on renewal_map entries specifing what to offer
        # Initilize Hardware Line Section if Needed
        if len(hardware_lines) == 0:
            hardware_lines.append(self.generate_section_line("$hardware").id)
            hardware_lines.append(self.generate_section_line("$block").id)

        renewal_maps = self.env["renewal.map"].search(
            [("product_id", "=", product.product_id.id)])

        if len(renewal_maps) != 1:
            return "Either a renewal map is missing, or there are too many renewal maps available for the " + str(product.product_id.name) + ". Amount of renewal maps found: (" + str(len(renewal_maps)) + ")\n\n"

        renewal_map = renewal_maps[0]
        hardware_lines.append(
            self.generate_section_line(product.formated_label, special="multiple").id
        )
        section_lines = []
        for map_product in renewal_map.product_offers:
            if (map_product.product_id.sale_ok):
                line = self.generate_product_line(
                    map_product.product_id, selected=map_product.selected
                )
                if str(type(line)) == "<class 'str'>":
                    return line
                section_lines.append(line.id)
        hardware_lines.extend(section_lines)

    def softwareCCP(self, software_lines, product):
        eid = product.name

        # Initilize Software Line Section If Needed
        if len(software_lines) == 0:
            software_lines.append(self.generate_section_line("$software").id)
            software_lines.append(self.generate_section_line("$block").id)

        product_list = self.env["product.product"].search(
            [("sku", "like", eid),
             ("active", "=", True),
             ("sale_ok", "=", True)])

        if len(product_list) != 1:
            return "Software CCP: Invalid Match Count (" + str(len(product_list)) + ") for \n[stock.lot].name: " + str(
                eid) + "\n[product.product].name: " + str(product.product_id.name) + "\n\n"

        line = self.generate_product_line(
            product_list[0], selected=True, optional="yes"
        )
        if str(type(line)) == "<class 'str'>":
            return line

        software_lines.append(line.id)

    def softwareSubCCP(self, software_sub_lines, product):
        eid = product.name

        # Initilize Sub Line Section If Needed
        if len(software_sub_lines) == 0:
            software_sub_lines.append(self.generate_section_line("$subscription").id)
            software_sub_lines.append(self.generate_section_line("$block").id)

        product_list = self.env["product.product"].search(
            [("sku", "like", eid),
             ("active", "=", True),
             ("sale_ok", "=", True)])

        if len(product_list) != 1:
            return "Software Subscritption CCP: Invalid Match Count (" + str(
                len(product_list)) + ") for\n[stock.lot].name: " + str(eid) + "\n[product.product].name: " + str(
                product.product_id.name) + "\n\n"

        if len(product_list) != 1:
            return "Software Subscritption CCP: Invalid Match Count (" + str(
                len(product_list)) + ") for\n[stock.lot].name: " + str(eid) + "\n[product.product].name: " + str(
                product.product_id.name) + "\n\n"

        line = self.generate_product_line(
            product_list[0], selected=True, optional="yes"
        )
        if str(type(line)) == "<class 'str'>":
            return line

        software_sub_lines.append(line.id)

    @api.onchange("sale_order_template_id", "renewal_product_items")
    def renewalQuoteAutoFill(self):
        # Verify Correct Template
        if self.sale_order_template_id.name == False:
            return
        if "Renewal Auto" not in self.sale_order_template_id.name:
            self.renewal_product_items = False
            return
        # Initilize Sections
        software_lines = []
        software_sub_lines = []
        hardware_lines = []
        error_msg = ""
        # For every product added to the quote add it to the correct section
        for product in self.renewal_product_items:

            _logger.error("------product display_name: " + str(product.display_name))
            _logger.error("------product product_id.name: " + str(product.product_id.name))
            _logger.error("------product.sku: " + str(product.sku))

            # only add product that can be sold
            if (product.product_id.sale_ok):
                if product.product_id.type_selection == "H":
                    _logger.info("Hardware")
                    msg = self.hardwareCCP(hardware_lines, product)
                elif product.product_id.type_selection == "S":
                    msg = self.softwareCCP(software_lines, product)
                    _logger.info("Software")
                elif product.product_id.type_selection == "SS":
                    msg = self.softwareSubCCP(software_sub_lines, product)
                    _logger.info("Software Subscription")
                else:
                    msg = (
                            "Product: "
                            + str(product.product_id.name)
                            + ' has unknown type "'
                            + str(product.product_id.type_selection)
                            + '"\n'
                    )
                if msg != None:
                    error_msg += msg + "\n"
            else:
                _logger.error("------product product_id.sale_ok is false, should not add product: ")

        # Combine Sections and add to quote
        lines = []
        lines.extend(hardware_lines)
        lines.extend(software_lines)
        lines.extend(software_sub_lines)
        self.order_line = [(6, 0, lines)]

        if error_msg != "":
            return {"warning": {"title": "Renewal Automation", "message": error_msg}}

    @api.depends_context('lang')
    @api.depends('order_line.tax_id', 'order_line.price_unit', 'amount_total', 'amount_untaxed', 'currency_id')
    def _compute_tax_totals(self):
        for order in self:
            order = order.with_company(order.company_id)
            order_lines = order.order_line.filtered(lambda x: not x.display_type and x.selected == "true")
            order.tax_totals = order.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )
            # _logger.info('>>>>>>>>>>>>>>>>. order.tax_totals: %s,', order.tax_totals)
            order.sudo().update({'amount_total': float(order.tax_totals['amount_total'])})

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        """ Create individual recipient groups with partner-specific tracking URLs, avoiding duplicates. """
        
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups
        self.ensure_one()


        # Get all potential recipients from various sources
        all_recipients = set()
        
        # From message partner_ids (when composing email)
        if msg_vals and msg_vals.get('partner_ids'):
            all_recipients.update(msg_vals['partner_ids'])
        
        # From message followers
        if hasattr(self, 'message_partner_ids'):
            all_recipients.update(self.message_partner_ids.ids)
            
        # From email_contacts field if it exists
        if hasattr(self, 'email_contacts') and self.email_contacts:
            all_recipients.update(self.email_contacts.ids)


        # Create new groups to insert BEFORE the original groups so they take precedence
        new_groups = []
        
        for partner_id in all_recipients:
            if not partner_id:
                continue
                
            partner = self.env['res.partner'].sudo().browse(partner_id)
            if not partner.exists():
                continue
                
            # Determine button title based on order state and partner language
            if self.state in ('draft', 'sent'):
                if partner.lang == 'fr_CA':
                    button_title = _("Voir le devis")
                elif partner.lang == 'es_ES':
                    button_title = _("Ver Cotización")
                else:
                    button_title = _("View Quotation")
            else:
                if partner.lang == 'fr_CA':
                    button_title = _("Voir la commande")
                elif partner.lang == 'es_ES':
                    button_title = _("Ver Orden")
                else:
                    button_title = _("View Order")
            
            # Generate partner-specific URL with their partner ID
            tracking_url = f"/check_quotation_redirect/{self.id}/{self.access_token}?user_id={partner_id}"
            
            _logger.info('>>>>>>>Creating group for partner %s with URL: %s', partner_id, tracking_url)
            
            # Create individual group for this partner that takes precedence
            new_groups.append([
                f'quote_recipient_{partner_id}',  # Unique group name
                lambda pdata, pid=partner_id: pdata['id'] == pid,  # Match only this partner
                {
                    'active': True,
                    'has_button_access': True,
                    'button_access': {
                        'url': tracking_url,
                        'title': button_title
                    },
                    'notification_group_name': f'quote_recipient_{partner_id}',
                    'recipients': []  # Will be populated during classification
                }
            ])

        # Disable original groups to prevent duplicates by setting them inactive
        for group in groups:
            group_name = group[0] 
            group_data = group[2]
            group_data['active'] = False  # Disable original groups
        
        
        # Return new groups + original groups (new groups take precedence due to order)
        return new_groups + groups
    
    def _notify_get_action_link(self, link_type, **kwargs):
        """ Override to add partner-specific user_id parameter to tracking URLs. """
        _logger.info('>>>>>>>_notify_get_action_link called with link_type: %s, kwargs: %s', link_type, kwargs)
        
        if link_type == 'view' and hasattr(self, 'access_token'):
            # Get the partner ID from kwargs - try different possible keys
            partner_id = kwargs.get('pid') or kwargs.get('partner_id') or kwargs.get('res_partner_id')
            _logger.info('>>>>>>>Found partner_id in _notify_get_action_link: %s', partner_id)
            
            if partner_id:
                # Generate partner-specific tracking URL
                url = f"/check_quotation_redirect/{self.id}/{self.access_token}?user_id={partner_id}"
                _logger.info('>>>>>>>Generated partner-specific URL in _notify_get_action_link: %s', url)
                return url
            else:
                # Fallback to default URL without user_id parameter
                url = f"/check_quotation_redirect/{self.id}/{self.access_token}"
                _logger.info('>>>>>>>Generated default URL in _notify_get_action_link: %s', url)
                return url
        
        # For other link types, use the parent implementation
        result = super()._notify_get_action_link(link_type, **kwargs)
        _logger.info('>>>>>>>Parent _notify_get_action_link returned: %s', result)
        return result

    def _notify_get_recipients_classify(self, message, recipients_data, model_description, msg_vals=None):
        """ Override to ensure each recipient gets partner-specific URL in their notification. """
        # Get the classified groups first
        groups = super()._notify_get_recipients_classify(message, recipients_data, model_description, msg_vals=msg_vals)
        
        _logger.info('>>>>>>>_notify_get_recipients_classify called with %s groups', len(groups))
        
        # Modify each group to ensure partner-specific URLs
        for group_data in groups:
            if 'button_access' in group_data and 'recipients' in group_data:
                recipients = group_data['recipients']
                _logger.info('>>>>>>>Processing group with recipients: %s', recipients)
                
                # If this group has exactly one recipient, update the URL to be partner-specific
                if len(recipients) == 1:
                    partner_id = recipients[0]
                    partner_url = f"/check_quotation_redirect/{self.id}/{self.access_token}?user_id={partner_id}"
                    group_data['button_access']['url'] = partner_url
                    _logger.info('>>>>>>>Updated group URL for partner %s: %s', partner_id, partner_url)
        
        return groups

    def _amount_all(self):
        # Ensure sale order lines are selected to included in calculation
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                if line.selected == "true" and line.sectionSelected == "true":
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax

            order.update(
                {
                    "amount_untaxed": amount_untaxed,
                    "amount_tax": amount_tax,
                    "amount_total": amount_untaxed + amount_tax,
                }
            )

    def _compute_amount_undiscounted(self):
        # Ensure sale order lines are selected to included in calculation
        for order in self:
            total = 0.0
            for line in order.order_line:
                if line.selected == "true" and line.sectionSelected == "true":
                    # why is there a discount in a field named amount_undiscounted ??
                    total += (
                            line.price_subtotal
                            + line.price_unit
                            * ((line.discount or 0.0) / 100.0)
                            * line.product_uom_qty
                    )
            order.amount_undiscounted = total

    def _amount_by_group(self):
        #  Overden Method to Ensure sale order lines are selected to included in calculation
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(
                formatLang,
                self.with_context(lang=order.partner_id.lang).env,
                currency_obj=currency,
            )
            res = {}
            for line in order.order_line:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.tax_id.compute_all(
                    price_reduce,
                    quantity=line.product_uom_qty,
                    product=line.product_id,
                    partner=order.partner_shipping_id,
                )["taxes"]
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {"amount": 0.0, "base": 0.0})
                    for t in taxes:
                        if line.selected != "true" or line.sectionSelected != "true":
                            break
                        if t["id"] == tax.id or t["id"] in tax.children_tax_ids.ids:
                            res[group]["amount"] += t["amount"]
                            res[group]["base"] += t["base"]
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.amount_by_group = [
                (
                    l[0].name,
                    l[1]["amount"],
                    l[1]["base"],
                    fmt(l[1]["amount"]),
                    fmt(l[1]["base"]),
                    len(res),
                )
                for l in res
            ]

    def _create_invoices(self, grouped=False, final=False, date=None):
        invoices = super()._create_invoices(grouped=grouped, final=final, date=date)

        for invoice in invoices:
            # Work on a stable order
            lines = invoice.invoice_line_ids.sorted('sequence')
            seq = 1
            commands = []

            for line in lines:
                # If our tag is present, insert a section just before this line
                if line.x_needs_section and line.x_section_label:
                    commands.append(Command.create({
                        'display_type': 'line_section',
                        'name': line.x_section_label,
                        'sequence': seq,
                    }))
                    seq += 1

                # Re-sequence the actual product line, and keep flags (no harm)
                commands.append(Command.update(line.id, {
                    'sequence': seq,
                }))
                seq += 1

            if commands:
                # Apply in one write to avoid flicker / resort
                invoice.write({'invoice_line_ids': commands})

        for order in self:
            if order.state != 'sale':
                continue  # Only handle confirmed orders

            for invoice in invoices.filtered(lambda inv: inv.invoice_origin == order.name):
                # Get all followers from the quote, excluding the customer
                follower_ids = order.message_partner_ids.filtered(
                    lambda p: p != order.partner_id
                ).ids

                if follower_ids:
                    invoice.message_subscribe(partner_ids=follower_ids)

        return invoices

class SaleOrderTemplateHandler(models.Model):
    _inherit = "sale.order"

    def _compute_line_data_for_template_change(self, line):
        return {
            'display_type': line.display_type,
            'name': line.name,
            'state': 'draft',
        }

    @api.model
    def _get_customer_lead(self, product_tmpl_id):
        return False
    
    @api.onchange('sale_order_template_id')
    def onchange_sale_order_template_id(self):
        
        # if not self.sale_order_template_id:
        #     self.require_signature = self._get_default_require_signature()
        #     self.require_payment = self._get_default_require_payment()
        #     return

        template = self.sale_order_template_id.with_context(lang=self.partner_id.lang)

        # --- first, process the list of products from the template
        order_lines = [(5, 0, 0)]
        for line in template.sale_order_template_line_ids:
            data = self._compute_line_data_for_template_change(line)
            data.update({
                'special': line.special,
                'hiddenSection': line.hiddenSection
            })

            if line.product_id:
                price = line.product_id.lst_price
                discount = 0

                if self.pricelist_id:
                    pricelist_price = self.pricelist_id.with_context(uom=line.product_uom_id.id)._get_product_price(line.product_id, 1, False)

                    if self.pricelist_id.discount_policy == 'without_discount' and price:
                        discount = max(0, (price - pricelist_price) * 100 / price)
                    else:
                        price = pricelist_price

                template_discount = getattr(line, 'discount', 0.0) or 0.0
                if template_discount:
                    discount = template_discount

                data.update({
                    'price_unit': price,
                    'discount': discount,
                    'product_uom_qty': line.product_uom_qty,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'optional': line.optional,
                    'selected': line.selected,
                    'sectionSelected': line.sectionSelected,
                    'quantityLocked': line.quantityLocked,
                    'customer_lead': self._get_customer_lead(line.product_id.product_tmpl_id),
                })

            order_lines.append((0, 0, data))

        self.order_line = order_lines
        self.order_line._compute_tax_id()

class PreconfigSaleOrder(models.Model):
    _inherit = 'sale.order'

    preconfigured_section_ids = fields.Many2many('preconfigured.section', string='Preconfigured Sections')

    @api.onchange('preconfigured_section_ids')
    def _onchange_preconfigured_sections(self):
        # Keep lines that are NOT from any preconfigured section
        non_preconfigured = self.order_line.filtered(lambda l: not l.preconfigured_section_id)

        # Build new virtual records for all currently selected sections
        new_lines = self.env['sale.order.line']
        for section in self.preconfigured_section_ids:
            new_lines |= self.env['sale.order.line'].new({
                'order_id': self.id,
                'name': section.section_name,
                'display_type': 'line_section',
                'preconfigured_section_id': section.id,
            })
            for pl in section.product_line_ids:
                new_lines |= self.env['sale.order.line'].new({
                    'order_id': self.id,
                    'product_id': pl.product_id.id,
                    'name': pl.product_name,
                    'optional': 'yes' if pl.optional else 'no',
                    'selected': 'true' if pl.selected else 'false',
                    'quantityLocked': 'yes' if pl.quantity_locked else 'no',
                    'price_unit': pl.price_unit,
                    'discount': pl.discount,
                    'product_uom_qty': 1,
                    'preconfigured_section_id': section.id,
                })

        self.order_line = non_preconfigured + new_lines