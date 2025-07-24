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

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class order(models.Model):
    _inherit = "sale.order"

    partner_id = fields.Many2one(
        'res.partner', 
        string="Customer",
        domain="[('is_company', '=', True)]",
        required=True
    )

    partner_name = fields.Char(string="Partner Name")
    rental_email = fields.Char(string="Email")

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
    financing_available = fields.Boolean(string="Financing Available")
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
        help="Footer selection field",
        string="Footer OLD",
    )

    header = fields.Selection(
        [
            ("QH_REALiT+Abtech.mp4", "QH_REALiT+Abtech.mp4"),
            ("ChurchXRAY.jpg", "ChurchXRAY.jpg"),
            ("Architecture.jpg", "Architecture.jpg"),
            ("Software.jpg", "Software.jpg"),
        ],
        string="Header OLD",
        help="Header selection field",
    )

    @api.onchange('sale_order_template_id')
    def _onchange_sale_order_template_id_set_header_footer(self):
        if self.sale_order_template_id and self.sale_order_template_id.header_id:
            self.header_id = self.sale_order_template_id.header_id
            # self.footer_id = self.sale_order_template_id.footer_id
    
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

    # this function adds sales@r-e-a-l.it as a follower automatically upon creation so it receives all the relevant emails
    @api.model
    def create(self, vals):
        order = super().create(vals)

        # Find or create the partner with email sales@r-e-a-l.it
        sales_email = self.env['res.partner'].search([('email', '=', 'sales@r-e-a-l.it')], limit=1)
        if sales_email:
            order.message_subscribe(partner_ids=[sales_email.id])

        # Add non-company partners to subscribers (automatic quotes from store)
        partner = order.partner_id
        if partner and not partner.is_company:
            if partner.id not in order.message_partner_ids.ids:
                order.message_subscribe(partner_ids=[partner.id])
        
        return order


    @api.model
    def default_get(self, fields_list):
        defaults = super(order, self).default_get(fields_list)

        # Search for the "Immediate Payment" payment term
        immediate_payment_term = self.env['account.payment.term'].search([('name', '=', 'Immediate Payment')], limit=1)
        
        # If found, set it as the default payment term
        if immediate_payment_term:
            defaults['payment_term_id'] = immediate_payment_term.id

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

    def _default_footer(self):
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

    def _default_header(self):
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

        # Get Prefered Headers
        result_raw = user.prefered_headers

        if result_raw != False:
            result = []
            for item in result_raw:
                # Verify headers are applicable for company
                if company in item.company_ids or len(item.company_ids) == 0:
                    result.append(item)
            if len(result) != 0:
                return result[-1]

        # Check for default footer that matches company
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Header"),
                ("default", "=", True),
                ("company_ids", "=", company.id),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        defaults = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Header"),
                ("default", "=", True),
                ("company_ids", "=", False),
            ]
        )
        if len(defaults) != 0:
            return defaults[-1]
        else:
            return False
            raise UserError("No Default Header Available")

    header_id = fields.Many2one("header.footer", default=_default_header, required=True)
    footer_id = fields.Many2one("header.footer", default=_default_footer, required=True)

    is_renewal = fields.Boolean(string="Renewal Quote", default=False)

    rental_start = fields.Date(string="Rental Start Date", default=False)
    rental_end = fields.Date(string="Rental End Date", default=False)

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

    def generate_product_line(
            self,
            product_id,
            *,
            selected=False,
            uom="Units",
            locked_qty="yes",
            optional="no"
    ):
        if selected == True:
            selected = "true"
        elif selected == False:
            selected = "false"

        product = self.env["product.product"].search([
            ("id", "=", product_id.id)])

        # Get Price
        pricelist = self.pricelist_id.id
        pricelist_entry = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id.id", "=", pricelist),
                ("product_tmpl_id.sku", "=", product.sku),
            ]
        )
        price = 0
        if len(pricelist_entry) > 1:
            return "Duplicate Pricelist Rules: " + str(product_id.sku)
        elif len(pricelist_entry) == 1:
            price = pricelist_entry[-1].fixed_price
        uomitem = self.env["uom.uom"].search([("name", "=", uom)])
        if len(product) != 1:
            return "Invalid Responses for: sku=" + str(product_id.sku)
        line = self.env["sale.order.line"].new(
            {
                "name": product.name,
                "selected": selected,
                "optional": optional,
                "quantityLocked": locked_qty,
                "product_id": product.id,
                "product_uom_qty": 1,
                "product_uom": uomitem,
                "price_unit": price,
                "order_id": self._origin.id,
            }
        )
        return line

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
        """ Give access button to all users and portal customers to view the quote in the portal. """
        
        groups = super()._notify_get_recipients_groups(
            message, model_description, msg_vals=msg_vals
        )
        if not self:
            return groups
        self.ensure_one()
        # Get the base URL for the portal
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        portal_url = self.get_portal_url()

        for group in groups:
            group_name = group[0]

            # enable the access button for all groups
            group[2]['has_button_access'] = True
            access_opt = group[2].setdefault('button_access', {})
            
            # set the title for the access button based on the state of the order
            if self.state in ('draft', 'sent'):
                if self.partner_id.lang == 'fr_CA':
                    access_opt['title'] = _("Voir le devis")
                else:
                    access_opt['title'] = _("View Quotation")
            else:
                if self.partner_id.lang == 'fr_CA':
                    access_opt['title'] = _("Voir la commande")
                else:
                    access_opt['title'] = _("View Order")
            
            # set the portal access URL for the button
            access_opt['url'] = f"/check_quotation_redirect/{self.id}/{self.access_token}"

        # return the modified recipient groups with the updated access options
        return groups

    def _amount_all(self):
        # Ensure sale order lines are selected to included in calculation
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                if line.selected == "true" and line.sectionSelected == "true":
                    if line.product_id.is_software:
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

                data.update({
                    'price_unit': price,
                    'discount': discount,
                    'product_uom_qty': line.product_uom_qty,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'optional': line.optional,
                    'selected':line.selected,
                    'sectionSelected':line.sectionSelected,
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
        if self.preconfigured_section_ids:
            new_lines = []
            for section in self.preconfigured_section_ids:
                new_lines.append((0, 0, {
                    'order_id': self.id,
                    'name': section.section_name,
                    'display_type': 'line_section',
                }))
                for line in section.product_line_ids:
                    new_lines.append((0, 0, {
                        'order_id': self.id,
                        'product_id': line.product_id.id,
                        'name': line.product_name,
                        'is_optional': line.optional,
                        'is_selected': line.selected,
                        'is_quantityLocked': line.quantity_locked,
                        'price_unit': line.price_unit,
                        'product_uom_qty': 1,
                    }))
            if new_lines:
                self.order_line = [(5, 0, 0)] + new_lines