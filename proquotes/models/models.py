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

from .translation import name_translation

_logger = logging.getLogger(__name__)


class purchase_order(models.Model):
    _inherit = 'purchase.order'
    footer = fields.Selection([
        ('ABtechFooter_Atlantic_Derek', "Abtech_Atlantic_Derek"),
        ('ABtechFooter_Atlantic_Ryan', "Abtech_Atlantic_Ryan"),
        ('ABtechFooter_Ontario_Derek', "Abtech_Ontario_Derek"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Ontario_Phil', "Abtech_Ontario_Phil"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Quebec_Alexandre', "Abtech_Quebec_Alexandre"),
        ('ABtechFooter_Quebec_Benoit_Carl', "ABtechFooter_Quebec_Benoit_Carl"),
        ('ABtechFooter_Quebec_Derek', "Abtech_Quebec_Derek"),
        ('GeoplusFooterCanada', "Geoplus_Canada"),
        ('GeoplusFooterUS', "Geoplus_America"),
        ('Leica_Footer_Ali', "Leica Ali"),
        ('REALiTFooter_Derek_US', "REALiTFooter_Derek_US"),
        ('REALiTSOLUTIONSLLCFooter_Derek_US', "R-E-A-L.iT Solutions Derek"),
        ('REALiTFooter_Derek', "REALiTFooter_Derek"),
        ('REALiTFooter_Derek_Transcanada', "REALiTFooter_Derek_Transcanada"),
    ], default='REALiTFooter_Derek', required=True, help="Footer selection field")


class invoice(models.Model):
    _inherit = 'account.move'
    footer = fields.Selection([
        ('ABtechFooter_Atlantic_Derek', "Abtech_Atlantic_Derek"),
        ('ABtechFooter_Atlantic_Ryan', "Abtech_Atlantic_Ryan"),
        ('ABtechFooter_Ontario_Derek', "Abtech_Ontario_Derek"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Ontario_Phil', "Abtech_Ontario_Phil"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Quebec_Alexandre', "Abtech_Quebec_Alexandre"),
        ('ABtechFooter_Quebec_Benoit_Carl', "ABtechFooter_Quebec_Benoit_Carl"),
        ('ABtechFooter_Quebec_Derek', "Abtech_Quebec_Derek"),
        ('GeoplusFooterCanada', "Geoplus_Canada"),
        ('GeoplusFooterUS', "Geoplus_America"),
        ('Leica_Footer_Ali', "Leica Ali"),
        ('REALiTFooter_Derek_US', "REALiTFooter_Derek_US"),
        ('REALiTSOLUTIONSLLCFooter_Derek_US', "R-E-A-L.iT Solutions Derek"),
        ('REALiTFooter_Derek', "REALiTFooter_Derek"),
        ('REALiTFooter_Derek_Transcanada', "REALiTFooter_Derek_Transcanada"),
    ], default='REALiTFooter_Derek', required=True, help="Footer selection field")


class order(models.Model):
    _inherit = 'sale.order'

    partner_ids = fields.Many2many(
        'res.partner', 'display_name', string="Contacts")

    products = fields.One2many(related="partner_id.products", readonly=True)

    customer_po_number = fields.Char(string="PO Number")
    # customer_po_file_name = fields.Char(string="PO File Name")
    # customer_po_file = fields.Binary(string="PO File")

    company_name = fields.Char(
        related="company_id.name", string="company_name", required=True)

    footer = fields.Selection([
        ('ABtechFooter_Atlantic_Derek', "Abtech_Atlantic_Derek"),
        ('ABtechFooter_Atlantic_Ryan', "Abtech_Atlantic_Ryan"),
        ('ABtechFooter_Ontario_Derek', "Abtech_Ontario_Derek"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Ontario_Phil', "Abtech_Ontario_Phil"),
        ('ABtechFooter_Ontario_Justin', "Abtech_Ontario_Justin"),
        ('ABtechFooter_Quebec_Alexandre', "Abtech_Quebec_Alexandre"),
        ('ABtechFooter_Quebec_Benoit_Carl', "ABtechFooter_Quebec_Benoit_Carl"),
        ('ABtechFooter_Quebec_Derek', "Abtech_Quebec_Derek"),
        ('GeoplusFooterCanada', "Geoplus_Canada"),
        ('GeoplusFooterUS', "Geoplus_America"),
        ('Leica_Footer_Ali', "Leica Ali"),
        ('REALiTFooter_Derek_US', "REALiTFooter_Derek_US"),
        ('REALiTSOLUTIONSLLCFooter_Derek_US', "R-E-A-L.iT Solutions Derek"),
        ('REALiTFooter_Derek', "REALiTFooter_Derek"),
        ('REALiTFooter_Derek_Transcanada', "REALiTFooter_Derek_Transcanada"),
    ], default='REALiTFooter_Derek', required=True, help="Footer selection field")

    header = fields.Selection([
        ('QH_REALiT+Abtech.mp4', "QH_REALiT+Abtech.mp4"),
        ('ChurchXRAY.jpg', "ChurchXRAY.jpg"),
        ('Architecture.jpg', "Architecture.jpg"),
        ('Software.jpg', "Software.jpg")], default='ChurchXRAY.jpg', required=True, help="Header selection field")

    is_rental = fields.Boolean(string="Rental Quote", default=False)
    rental_diff_add = fields.Boolean(string="Rental Address", default=False)
    rental_street = fields.Char(string="Street Address")
    rental_city = fields.Char(string="City")
    rental_zip = fields.Char(string="ZIP/Postal Code")
    rental_state = fields.Many2one(
        "res.country.state", string="State/Province", store="true")
    rental_country = fields.Many2one(
        "res.country", string="Country", store="true")

    rental_start = fields.Date(string="Rental Start Date", default=False)
    rental_end = fields.Date(string="Rental End Date", default=False)
    # rental_insurance = fields.Binary(string="Insurance")

    @ api.onchange('sale_order_template_id')
    def set_is_rental(self):
        if (self.sale_order_template_id.name == "Rental"):
            self.is_rental = True
        else:
            self.is_rental = False

    def generate_section_line(self, name, *, special="regular", selected='true'):
        section = self.env['sale.order.line'].create(
            {'name': name, 'special': special, 'display_type': 'line_section', 'order_id': self._origin.id, 'selected': selected})
        return section

    def generate_product_line(self, sku, *, selected='true', locked_qty='true', optional='true'):
        product = self.env['product.template'].search([('sku', '=', sku)])
        _logger.error(product.id)
        line = self.env['sale.order.line'].create(
            {'name': product.name,
             'product_id': product.id,
             'selected': selected,
             'optional': optional,
             'quantityLocked': locked_qty,
             'order_id': self._origin.id})
        _logger.warning(line)
        return line

    @api.onchange('sale_order_template_id')
    def renewalQuoteAutoFill(self):
        if (not "Renewal Auto" in self.sale_order_template_id.name):
            return
        for product in self.products:
            if (product.product_id.sku == "838300"):
                _logger.warning("RTC")
                block = self.generate_section_line("$block")
                _logger.warning("HERE")
                section = self.generate_section_line(
                    product.formated_label, special="multiple")
                addList = [block.id, section.id]
                line = self.generate_product_line(6013561)
                addList.append(line.id)
                for lineItem in addList:
                    _logger.error(lineItem)
                self.order_line = [(6, 0, addList)]

    def _amount_all(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.order_line:
                if (line.selected == 'true' and line.sectionSelected == 'true'):
                    amount_untaxed += line.price_subtotal
                    amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })

    def _compute_amount_undiscounted(self):
        for order in self:
            total = 0.0
            for line in order.order_line:
                if (line.selected == 'true' and line.sectionSelected == 'true'):
                    # why is there a discount in a field named amount_undiscounted ??
                    total += line.price_subtotal + line.price_unit * \
                        ((line.discount or 0.0) / 100.0) * line.product_uom_qty
            order.amount_undiscounted = total

    def _amount_by_group(self):
        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            fmt = partial(formatLang, self.with_context(
                lang=order.partner_id.lang).env, currency_obj=currency)
            res = {}
            for line in order.order_line:
                price_reduce = line.price_unit * (1.0 - line.discount / 100.0)
                taxes = line.tax_id.compute_all(
                    price_reduce, quantity=line.product_uom_qty, product=line.product_id, partner=order.partner_shipping_id)['taxes']
                for tax in line.tax_id:
                    group = tax.tax_group_id
                    res.setdefault(group, {'amount': 0.0, 'base': 0.0})
                    for t in taxes:
                        if (line.selected != 'true' or line.sectionSelected != 'true'):
                            break
                        if (t['id'] == tax.id or t['id'] in tax.children_tax_ids.ids):
                            res[group]['amount'] += t['amount']
                            res[group]['base'] += t['base']
            res = sorted(res.items(), key=lambda l: l[0].sequence)
            order.amount_by_group = [(
                l[0].name, l[1]['amount'], l[1]['base'],
                fmt(l[1]['amount']), fmt(l[1]['base']),
                len(res),
            ) for l in res]


class orderLineProquotes(models.Model):
    _inherit = 'sale.order.line'

    variant = fields.Many2one('proquotes.variant', string="Variant Group")

    applied_name = fields.Char(
        compute='get_applied_name', string="Applied Name")

    selected = fields.Selection([
        ('true', "Yes"),
        ('false', "No")], default="true", required=True, help="Field to Mark Wether Customer has Selected Product")

    sectionSelected = fields.Selection([
        ('true', "Yes"),
        ('false', "No")], default="true", required=True, help="Field to Mark Wether Container Section is Selected")

    special = fields.Selection([
        ('regular', "regular"),
        ('multiple', "Multiple"),
        ('optional', "Optional")], default='regular', required=True, help="Technical field for UX purpose.")

    hiddenSection = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default='no', required=True, help="Field To Track if Sections are folded")

    optional = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], default="no", required=True, help="Field to Mark Product as Optional")

    quantityLocked = fields.Selection([
        ('yes', "Yes"),
        ('no', "No")], string="Lock Quantity", default="yes", required=True, help="Field to Lock Quantity on Products")

    def get_applied_name(self):
        n = name_translation(self)
        n.get_applied_name()

    def get_sale_order_line_multiline_description_sale(self, product):
        if product.description_sale:
            return product.description_sale
        else:
            return "<span></span>"


class proquotesMail(models.TransientModel):
    _inherit = 'mail.compose.message'

    def generate_email_for_composer(self, template_id, res_ids, fields):
        """ Call email_template.generate_email(), get fields relevant for
                mail.compose.message, transform email_cc and email_to into partner_ids """
        multi_mode = True
        if isinstance(res_ids, int):
            multi_mode = False
            res_ids = [res_ids]

        returned_fields = fields + ['partner_ids', 'attachments']
        values = dict.fromkeys(res_ids, False)

        template_values = self.env['mail.template'].with_context(
            tpl_partners_only=True).browse(template_id).generate_email(res_ids, fields)
        for res_id in res_ids:
            res_id_values = dict((field, template_values[res_id][field])
                                 for field in returned_fields if template_values[res_id].get(field))
            res_id_values['body'] = res_id_values.pop('body_html', '')
            if template_values[res_id].get('model') == 'sale.order':
                res_id_values['partner_ids'] = self.env['sale.order'].browse(
                    res_id).partner_ids + self.env['res.partner'].search([('email', '=', 'sales@r-e-a-l.it')])
            values[res_id] = res_id_values
        return multi_mode and values or values[res_ids[0]]


class variant(models.Model):
    _name = 'proquotes.variant'
    _description = "Model that Represents Variants for Customer Multi-Level Choices"

    name = fields.Char(string='Variant Group', required=True,
                       copy=False, index=True, default="New")

    rule = fields.Char(string="Variant Rule", required=True, default="None")


class person(models.Model):
    _inherit = "res.partner"

    products = fields.One2many(
        'stock.production.lot', 'owner', string="Products")


class owner(models.Model):
    _inherit = "stock.production.lot"

    owner = fields.Many2one('res.partner', string="Owner")

    def copy_label(self):
        # Form Button Needs a Python Target Function
        return


# pdf footer

class pdf_quote(models.Model):
    _inherit = "sale.report"

    footer_field = fields.Selection(related="order_id.footer")
