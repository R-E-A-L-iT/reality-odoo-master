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

    footer = fields.Selection(
        [
            ("ABtechFooter_Atlantic_Derek", "Abtech_Atlantic_Derek"),
            ("ABtechFooter_Atlantic_Ryan", "Abtech_Atlantic_Ryan"),
            ("ABtechFooter_Ontario_Derek", "Abtech_Ontario_Derek"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Ontario_Phil", "Abtech_Ontario_Phil"),
            ("ABtechFooter_Ontario_Justin", "Abtech_Ontario_Justin"),
            ("ABtechFooter_Quebec_Alexandre", "Abtech_Quebec_Alexandre"),
            ("ABtechFooter_Quebec_Benoit_Carl", "ABtechFooter_Quebec_Benoit_Carl"),
            ("ABtechFooter_Quebec_Derek", "Abtech_Quebec_Derek"),
            ("GeoplusFooterCanada", "Geoplus_Canada"),
            ("GeoplusFooterUS", "Geoplus_America"),
            ("Leica_Footer_Ali", "Leica Ali"),
            ("REALiTFooter_Derek_US", "REALiTFooter_Derek_US"),
            ("REALiTFooter_Martin", "REALiTFooter_Martin"),
            ("REALiTSOLUTIONSLLCFooter_Derek_US", "R-E-A-L.iT Solutions Derek"),
            ("REALiTFooter_Derek", "REALiTFooter_Derek"),
            ("REALiTFooter_Derek_Transcanada", "REALiTFooter_Derek_Transcanada"),
        ],
        default="REALiTFooter_Derek",
        required=True,
        string="Footer OLD",
        help="Footer selection field",
    )

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
            else:
                formatted_date = expiry_date_obj.strftime('%d %B, %Y')

            product = self.env['product.product'].search([('name', '=', product_code)], limit=1)
            if product:
                product_name = product.with_context(lang=self.env.context.get('lang', 'en_US')).name

            if self.env.context.get('lang') == 'fr_CA':
                new_label = f"{product_name} ({parts[1]}) - Expiration: {formatted_date}"
            else:
                new_label = f"{product_name} ({parts[1]}) - Expiration: {formatted_date}"

            return new_label
        except Exception:
            return label

    @api.depends("company_id")
    def _get_default_footer(self):
        # Get Company
        company = None
        if self.company_id == False or self.company_id == None:
            company = self.company_id
        else:
            company = self.env.company

        # Get User
        user = None
        if self.user_id == False or self.user_id == None:
            user = self.user_id
        else:
            user = self.env.user

        # Get Prefered Footers
        result_raw = user.prefered_quote_footers

        if result_raw != False:
            result = []
            for item in result_raw:
                # Verify footers are applicable for company
                if company in item.company_ids or len(item.company_ids) == 0:
                    result.append(item)
            if len(result) != 0:
                return result[-1]

        # Check for default footer that matches company
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", company.id),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
                ("default", "=", True),
                ("company_ids", "=", False),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        else:
            return False
            raise UserError("No Default Footer Available")

    footer_id = fields.Many2one(
        "header.footer", required=True, default=_get_default_footer
    )
    
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
    def create(self, vals):
        invoice_object = super(invoice, self).create(vals)

        if invoice_object.move_type not in ['out_invoice', 'out_refund']:
            return invoice_object

        # Ensure invoice inherits correct company from website sale order
        self._set_company_from_sale_order(invoice_object)

        # add sales@r-e-a-l.it as a follower of the document
        if invoice_object.move_type in ['out_invoice', 'out_refund']:
            partner = self.env['res.partner'].search([('email', '=', 'sales@r-e-a-l.it')], limit=1)
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

        return invoice_object

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