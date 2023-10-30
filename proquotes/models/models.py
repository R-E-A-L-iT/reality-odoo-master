# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re

from datetime import date, datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

from .translation import name_translation

_logger = logging.getLogger(__name__)


class purchase_order(models.Model):
    _inherit = "purchase.order"
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
        else:
            return False
            raise UserError("No Default Footer Available")

    footer_id = fields.Many2one(
        "header.footer", default=_get_default_footer, required="True"
    )


class invoice(models.Model):
    _inherit = "account.move"
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


class order(models.Model):    
    _inherit = "sale.order"

    partner_ids = fields.Many2many("res.partner", "display_name", string="Contacts")
    products = fields.One2many(related="partner_id.products", readonly=True)
    customer_po_number = fields.Char(string="PO Number")
    company_name = fields.Char(related="company_id.name", string="company_name", required=True)

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

    is_rental = fields.Boolean(string="Rental Quote", default=False)
    is_renewal = fields.Boolean(string="Renewal Quote", default=False)

    rental_diff_add = fields.Boolean(string="Rental Address", default=False)
    rental_street = fields.Char(string="Street Address")
    rental_city = fields.Char(string="City")
    rental_zip = fields.Char(string="ZIP/Postal Code")
    rental_state = fields.Many2one("res.country.state", string="State/Province", store="true")
    rental_country = fields.Many2one("res.country", string="Country", store="true")
    rental_start = fields.Date(string="Rental Start Date", default=False)
    rental_end = fields.Date(string="Rental End Date", default=False)
    renewal_product_items = fields.Many2many(string="Renewal Items", comodel_name="stock.production.lot")

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



    @api.onchange("sale_order_template_id")
    def set_sale_order_flags(self):
        # Set a flag if quotes is a rental quote        
        if "rental" in str(self.sale_order_template_id.name).lower():
            self.is_rental = True
            self.setRentalDiscount()                 
        else:
            self.is_rental = False
            #_logger.error("is_rental FALSE, " + str(self.sale_order_template_id.name))
            
        if (self.sale_order_template_id.name != False and "Renewal" in self.sale_order_template_id.name):
            self.is_renewal = True
        else:
            self.is_renewal = False
        
        self.setPricelist()

    #Company dans le context (RealIT, Solution,  US, ...)
    @api.onchange("company_id")
    def printTest(self):
        _logger.error("company_id: " + str(self.company_id))
        _logger.error("company_name: " + str(self.company_name))


    @api.onchange("pricelist_id")
    def pricelistChanged(self):
        self.setRentalDiscount()


    #Business (compagnie à qui on fait la location)
    @api.onchange("partner_id")
    def printTest2(self):       
        self.setPricelist()


    #Methode to set the first item of a rental kit to 0% discount, and all the reste of the kit at 100% discounte
    def setRentalDiscount(self):
        if(self.is_rental):
            activateDiscount = False
            firstItem = True
            #_logger.error("is_rental TRUE, " + str(self.sale_order_template_id.name))     
            for line in self.order_line:
                    
                if (line.name == "$block+"):
                    continue

                if ("#" in line.name):
                    if ("RENTAL KIT" in line.name):
                        _logger.error("activateDiscount = True")     
                        activateDiscount = True
                        continue
                    else:
                        _logger.error("activateDiscount = False")     
                        activateDiscount = False
                        firstItem = True
                        continue

                if(activateDiscount):
                    #_logger.error("line name discounted: " + str(line.name))  
                    if (firstItem):
                        line.reservation_begin  = datetime(2023, 10, 28, 16, 0) 
                        firstItem = False
                        _logger.error("activateDiscount----- firstItem not discounted: " + str(line.name))
                    else:
                        line.discount = 100   
                        line.rental_updatable = True 
                        _logger.error("activateDiscount----- discounted: " + str(line.name))
                else:
                    _logger.error("line name: " + str(line.name))    


    # Methot do update the pricelist base on the current partner_id of the sale_order.
    def setPricelist(self):
        country_id = int(self.partner_id.country_id)
        if (country_id >= 0):
            country = self.env["res.country"].search([("id", "=", country_id)])
            #_logger.error("country.name: " + str(country.name))

            currency_id = int(country.currency_id)
            if (currency_id >= 0):
                currency = self.env["res.currency"].search([("id", "=", currency_id)])
                # _logger.error("currency.id: " + str(currency.id))
                # _logger.error("currency.name: " + str(currency.name))

                #not a good management, create more user problem since when updating price, the discount does aways.
                if (self.is_rental):
                    pricelist_array = self.env["product.pricelist"].search([("currency_id", "=", currency_id), ("name", "ilike", "RENTAL")])
                    if (len(pricelist_array) == 1):
                        self.pricelist_id = pricelist_array[0]
                        #_logger.error("self.pricelist_id: " + str(self.pricelist_id))
                        #would be nice to update the price list but I can't find the method "update prices"
                else:
                    pricelist_array = self.env["product.pricelist"].search([("currency_id", "=", currency_id), ("name", "ilike", "SALE")])
                    if (len(pricelist_array) == 1):
                        self.pricelist_id = pricelist_array[0]
                        #_logger.error("self.pricelist_id: " + str(self.pricelist_id))
                        #would be nice to update the price list but I can't find the method "update prices"
        

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
        product = self.env["product.product"].search([("id", "=", product_id.id)])
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
        # Generate lines based on renewal_map entries specifing what to offer

        # Initilize Hardware Line Section if Needed
        if len(hardware_lines) == 0:
            hardware_lines.append(self.generate_section_line("$hardware").id)
            hardware_lines.append(self.generate_section_line("$block").id)
        renewal_maps = self.env["renewal.map"].search(
            [("product_id", "=", product.product_id.id)]
        )
        if len(renewal_maps) != 1:
            return "No Mapping for: " + str(product.product_id.name)
        renewal_map = renewal_maps[0]
        hardware_lines.append(
            self.generate_section_line(product.formated_label, special="multiple").id
        )
        section_lines = []
        for map_product in renewal_map.product_offers:
            line = self.generate_product_line(
                map_product.product_id, selected=map_product.selected
            )
            if str(type(line)) == "<class 'str'>":
                return line
            section_lines.append(line.id)
        hardware_lines.extend(section_lines)

    def softwareCCP(self, software_lines, product):
        # Initilize Software Line Section If Needed
        if len(software_lines) == 0:
            software_lines.append(self.generate_section_line("$software").id)
            software_lines.append(self.generate_section_line("$block").id)
        eid = product.name
        product_list = self.env["product.product"].search(
            [("sku", "like", eid), ("active", "=", True)]
        )
        if len(product_list) != 1:
            return "Invalid Match Count for EID: " + str(eid)

        line = self.generate_product_line(
            product_list[0], selected=True, optional="yes"
        )
        if str(type(line)) == "<class 'str'>":
            return line
        software_lines.append(line.id)

    def softwareSubCCP(self, software_sub_lines, product):
        # Initilize Sub Line Section If Needed
        if len(software_sub_lines) == 0:
            software_sub_lines.append(self.generate_section_line("$subscription").id)
            software_sub_lines.append(self.generate_section_line("$block").id)
        eid = product.name
        product_list = self.env["product.product"].search(
            [("sku", "like", eid), ("active", "=", True)]
        )
        if len(product_list) != 1:
            return "Invalid Match Count for EID: " + str(eid)

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
            if product.product_id.type_selection == "H":
                _logger.info("Hardware")
                msg = self.hardwareCCP(hardware_lines, product)
            elif product.product_id.type_selection == "S":
                msg = self.softwareCCP(software_lines, product)
                _logger.info("Softare")
            elif product.product_id.type_selection == "SS":
                msg = self.softwareSubCCP(software_sub_lines, product)
                _logger.info("Software Subscription")
            else:
                msg = (
                    "Product: "
                    + str(product.product_id.name)
                    + ' has unknown type "'
                    + str(product.product_id.type_selection)
                    + '"'
                )
            if msg != None:
                error_msg += msg + "\n"

        # Combine Sections and add to quote
        lines = []
        lines.extend(hardware_lines)
        lines.extend(software_lines)
        lines.extend(software_sub_lines)
        self.order_line = [(6, 0, lines)]

        if error_msg != "":
            return {"warning": {"title": "Renewal Automation", "message": error_msg}}

    def calc_rental_price(self, price):
        # Take into account length of rental
        if self.rental_start == False or self.rental_end == False:
            return price

        # Calculate Rental Length
        sdate = str(self.rental_start).split("-")
        edate = str(self.rental_end).split("-")
        rentalDays = (
            date(int(edate[0]), int(edate[1]), int(edate[2]))
            - date(int(sdate[0]), int(sdate[1]), int(sdate[2]))
        ).days
        rentalMonths = rentalDays // 30
        rentalDays = rentalDays % 30
        rentalWeeks = rentalDays // 7
        rentalDays = rentalDays % 7

        # Calulate Rental Price based on rental length
        rentalRate = 0
        rentalDayRate = price * rentalDays
        if rentalDayRate > price * 4:
            rentalDayRate = price * 4
        rentalWeekDayRate = 4 * price * rentalWeeks + rentalDayRate
        if rentalWeekDayRate > price * 12:
            rentalDayRate = price * 12
        rentalMonthRate = 12 * price * rentalMonths
        return rentalRate + rentalMonthRate + rentalWeekDayRate

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


class orderLineProquotes(models.Model):
    _inherit = "sale.order.line"

    variant = fields.Many2one("proquotes.variant", string="Variant Group")

    applied_name = fields.Char(compute="get_applied_name", string="Applied Name")

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

    def get_applied_name(self):
        n = name_translation(self)
        n.get_applied_name()

    def get_sale_order_line_multiline_description_sale(self, product):
        if product.description_sale:
            return product.description_sale
        else:
            return "<span></span>"
    



class proquotesMail(models.TransientModel):
    _inherit = "mail.compose.message"

    def generate_email_for_composer(self, template_id, res_ids, fields):
        """Call email_template.generate_email(), get fields relevant for
        mail.compose.message, transform email_cc and email_to into partner_ids"""
        # Overriden to define the default recipients of a message.
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]

        returned_fields = fields + ["partner_ids", "attachments"]
        values = dict.fromkeys(res_ids, False)

        template_values = (
            self.env["mail.template"]
            .with_context(tpl_partners_only=True)
            .browse(template_id)
            .generate_email(res_ids, fields)
        )
        for res_id in res_ids:
            res_id_values = dict(
                (field, template_values[res_id][field])
                for field in returned_fields
                if template_values[res_id].get(field)
            )
            res_id_values["body"] = res_id_values.pop("body_html", "")
            if template_values[res_id].get("model") == "sale.order":
                res_id_values["partner_ids"] = self.env["sale.order"].browse(
                    res_id
                ).partner_ids + self.env["res.partner"].search(
                    [("email", "=", "sales@r-e-a-l.it")]
                )
            values[res_id] = res_id_values
        return multi_mode and values or values[res_ids[0]]


class variant(models.Model):
    _name = "proquotes.variant"
    _description = "Model that Represents Variants for Customer Multi-Level Choices"

    name = fields.Char(
        string="Variant Group", required=True, copy=False, index=True, default="New"
    )

    rule = fields.Char(string="Variant Rule", required=True, default="None")


class person(models.Model):
    _inherit = "res.partner"

    products = fields.One2many("stock.production.lot", "owner", string="Products")


class owner(models.Model):
    _inherit = "stock.production.lot"

    owner = fields.Many2one("res.partner", string="Owner")

    def copy_label(self):
        # Form Button Needs a Python Target Function
        return


# pdf footer


class pdf_quote(models.Model):
    _inherit = "sale.report"

    footer_field = fields.Selection(related="order_id.footer")
