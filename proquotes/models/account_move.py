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

class invoice(models.Model):
    _inherit = "account.move"

    customer_po_number = fields.Char(
        compute="_compute_customer_po_number",
        store=True
    )

    def action_thank_you_email(self):
        """
        Open the email compose wizard with our 'thank you' template
        """
        self.ensure_one()
        template = self.env.ref('proquotes.email_template_invoice_thank_you')
        # Use the built-in mail.compose.message wizard
        compose_ctx = dict(
            default_model='account.move',
            default_res_ids=[self.id],
            default_use_template=bool(template),
            default_template_id=template and template.id or False,
            default_composition_mode='comment',
        )
        return {
            'name': _('Send Thank You'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'target': 'new',
            'context': compose_ctx,
        }

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        # Exclude the invoice's customer from being subscribed
        partner_ids = [
            pid for pid in (partner_ids or [])
            if pid not in self.mapped('partner_id').ids
        ]
        if not partner_ids:
            return
        return super().message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)

    @api.depends('invoice_origin')
    def _compute_customer_po_number(self):
        for move in self:
            order = self.env['sale.order'].search([('name', '=', move.invoice_origin)], limit=1)
            move.customer_po_number = order.customer_po_number or ''

    email_partner_ids = fields.Many2many('res.partner', string="Email Recipients (from wizard)")

    def _get_available_footer_domain(self):
        return [
            ("active", "=", True),
            ("record_type", "=", "Footer"),
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
    def _get_user_company_footer(self, user=False, company=False):
        user = user or self.env.user
        company = company or self.env.company

        if not user or not company:
            return self.env["header.footer"]

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

    footer_id = fields.Many2one(
        "header.footer",
        string="Footer",
        required=True,
        domain="[('active', '=', True), ('record_type', '=', 'Footer')]",
        default=_default_footer_id,
    )

    @api.onchange("invoice_user_id", "company_id")
    def _onchange_invoice_user_or_company_set_footer(self):
        for move in self:
            company = move.company_id or self.env.company
            user = move.invoice_user_id or self.env.user

            footer = move._get_user_company_footer(user=user, company=company)
            if not footer:
                footer = move._get_company_default_footer(company=company)
            if not footer:
                footer = move._get_first_available_footer(company=company)

            move.footer_id = footer.id if footer else False

    def action_invoice_sent(self):
        """ Open a window to compose an email, with the edi invoice template
            message loaded by default
        """
        self.ensure_one()

        if self.invoice_pdf_report_id:
            self.invoice_pdf_report_id.unlink()

        report_action = self.action_send_and_print()
        if self.env.is_admin() and not self.env.company.external_report_layout_id and not self.env.context.get(
                'discard_logo_check'):
            return self.env['ir.actions.report']._action_configure_external_report_layout(report_action)

        return report_action

    def get_translated_term(self, title, lang):
        if "translate" in title:

            _logger.info("PDF QUOTE - TRANSLATION FUNCTION ACTIVATED")
            terms =  title.split("+",2)

            if terms[0] == "#translate":
                english = terms[1]
                french = terms[2]

                if lang == 'fr_CA':
                    return french
                else:
                    return english

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
                month_name = expiry_date_obj.strftime('%B').capitalize()
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
    
    payment_date = fields.Char(string="Date of Payment", compute="_compute_payment_date", copy=False)
    
    def _compute_payment_date(self):
        for rec in self:
            rec.payment_date = False
            if rec.invoice_payments_widget:
                data = rec.invoice_payments_widget
                if data.get('content'):
                    payment_dates = set()
                    for payment in data['content']:
                        payment_date = payment['date']
                        formatted_date = payment_date.strftime('%d/%m/%Y')
                        payment_dates.add(formatted_date)
                    # For multi payment.
                    rec.payment_date = ', '.join(sorted(payment_dates))
                else:
                    rec.payment_date = False

    def action_post(self):
        res = super().action_post()
        for move in self:
            if move.move_type == "out_invoice" and move.name:
                company = move.company_id
                if company.name == "R-E-A-L.iT Solutions":
                    custom_prefix = "CAN-INV/"
                elif company.name == "R-E-A-L.iT U.S. Inc.":
                    custom_prefix = "USA-INV/"
                else:
                    _logger.info("Using default Odoo sequence for %s", company.name)
                    continue  # Odoo's default
                if not move.name.startswith(custom_prefix):
                    new_name = f"{custom_prefix}{move.name}"
                    _logger.info("Renaming Invoice: %s -> %s", move.name, new_name)
                    move.name = new_name
        return res

    def _set_company_from_sale_order(self, invoice):
        """Inherit company from originating sale order if it's a website order"""
        if invoice.move_type not in ['out_invoice', 'out_refund']:
            return

        # Find the related sale orders
        sale_orders = invoice.invoice_line_ids.mapped('sale_line_ids.order_id')

        if sale_orders:
            # Use the first sale order's company (typically all lines from same order)
            first_order = sale_orders[0]

            # If the sale order is from website, ensure invoice uses same company
            if first_order.website_id and first_order.company_id:
                if invoice.company_id != first_order.company_id:
                    _logger.info('>>>>>>>Setting invoice company from website sale order: %s', first_order.company_id.name)
                    invoice.company_id = first_order.company_id.id

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        user_id = defaults.get("invoice_user_id") or self.env.uid
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

        return defaults

    # Odoo 19: create is @api.model_create_multi (receives a list of vals dicts).
    @api.model_create_multi
    def create(self, vals_list):
        invoices = super(invoice, self).create(vals_list)

        for invoice_object in invoices:
            if invoice_object.move_type not in ['out_invoice', 'out_refund']:
                continue

            # Ensure invoice inherits correct company from website sale order
            self._set_company_from_sale_order(invoice_object)

            # add derek@r-e-a-l.it as a follower of the document
            if invoice_object.move_type in ['out_invoice', 'out_refund']:
                partner = self.env['res.partner'].search([('id', '=', '58319')], limit=1)
                if partner and partner.id not in invoice_object.message_partner_ids.ids:
                    invoice_object.message_subscribe(partner_ids=[partner.id])

            # Find the related sale orders
            sale_orders = invoice_object.invoice_line_ids.mapped('sale_line_ids.order_id')

            for order in sale_orders:
                for line in invoice_object.invoice_line_ids:
                    # Get the corresponding sale order line
                    sale_line = line.sale_line_ids.filtered(lambda l: l.order_id == order)

                    # Remove the invoice line if the related sale line is not selected
                    if sale_line and not sale_line.selected:
                        line.unlink()

        return invoices

class InvoiceMain(models.Model):
    _inherit = "account.move"
    pricelist_id = fields.Many2one("product.pricelist", string="Pricelist")

    # Setup Initilize Pricelist for Invoice
    @api.onchange("partner_id")
    def _setpricelist(self):
        self.pricelist_id = self.partner_id.property_product_pricelist

    def _calculate_tax(self, price, tax_obj):
        if tax_obj.amount_type != "group" :
            _logger.info("amount: " + str(tax_obj.amount))
            return round(price * tax_obj.amount / 100, 2)

        result = 0

        for child in tax_obj.children_tax_ids:
            result += self._calculate_tax(price, child)

        _logger.info(result)
        return result