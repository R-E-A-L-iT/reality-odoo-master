# -*- coding: utf-8 -*-

from odoo import api, fields, models
from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _
from odoo.exceptions import RedirectWarning, AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo.tools.translate import _
from odoo import models, fields, api
_logger = logging.getLogger(__name__)

class product(models.Model):
    _inherit = "product.template"

    service_policy = [
        ('ordered_prepaid', 'Prepaid/Fixed Price'),
        ('delivered_manual', 'Based on Delivered Quantity (Manual)'),
        ('delivered_milestones', 'Based on Milestones'),
        ('delivered_timesheet', 'Based on Timesheets')
    ]

    cadVal = fields.Monetary(string="Canadian Product Value")
    usdVal = fields.Monetary(string="United States Product Value")
    type_selection = fields.Selection(
        [("H", "H"), ("S", "S"), ("SS", "SS")], string="Type (H/S/SS)", default=False
    )
    is_software = fields.Boolean(string="Is Software", default=False)
    service_policy = fields.Selection(service_policy, string="Service Invoicing Policy", compute_sudo=True, compute='_compute_service_policy', inverse='_inverse_service_policy')

    @api.depends('invoice_policy', 'service_type', 'type')
    def _compute_service_policy(self):
        for product in self:
            product.service_policy = self._get_general_to_service(product.invoice_policy, product.service_type)
            if not product.service_policy:
                if product.type == 'service':
                    product.service_policy = 'ordered_prepaid'
                else:
                    product.service_policy = 'delivered_manual'

    @api.model
    def search_fetch(self, domain, field_names, offset=0, limit=None, order=None):
        # if self.env.context.get('only_media'):
        #     domain += [('name', '=', 'Media')]
        if domain:
            for arg in domain:
                if isinstance(arg, (list, tuple)) and arg[0] == 'name' and isinstance(arg[2], str):
                    product_ids = []
                    product_name_search = '%'+arg[2]+'%'
                    query_select_name = _("select id from product_template join jsonb_each_text(product_template.name) e on true where LOWER(e.value) like LOWER('%s')") % (product_name_search)
                    self._cr.execute(query_select_name)
                    values_name = self._cr.fetchall()
                    for value_nm in values_name:
                        product_ids.append(int(value_nm[0]))

                    query_select_other = _("select id from product_template where default_code like '%s'") % (arg[2])
                    self._cr.execute(query_select_other)
                    values_other = self._cr.fetchall()
                    for value_ot in values_other:
                        product_ids.append(int(value_ot[0]))
                    
                    domain = [['id', 'in', product_ids]]
        return super().search_fetch(domain, field_names, offset, limit, order)
                

class ProductProduct(models.Model):
    _inherit = "product.product"

    price = fields.Float(
        'Price', compute='_compute_product_price',
        digits='Product Price', inverse='_set_product_price')

    @api.depends_context('pricelist', 'partner', 'quantity', 'uom', 'date', 'no_variant_attributes_price_extra')
    def _compute_product_price(self):
        prices = {}
        pricelist_id_or_name = self._context.get('pricelist')
        if pricelist_id_or_name:
            pricelist = None
            partner = self.env.context.get('partner', False)
            quantity = self.env.context.get('quantity', 1.0)

            # Support context pricelists specified as list, display_name or ID for compatibility
            if isinstance(pricelist_id_or_name, list):
                pricelist_id_or_name = pricelist_id_or_name[0]
            if isinstance(pricelist_id_or_name, str):
                pricelist_name_search = self.env['product.pricelist'].name_search(pricelist_id_or_name, operator='=',
                                                                                  limit=1)
                if pricelist_name_search:
                    pricelist = self.env['product.pricelist'].browse([pricelist_name_search[0][0]])
            elif isinstance(pricelist_id_or_name, int):
                pricelist = self.env['product.pricelist'].browse(pricelist_id_or_name)

            if pricelist:
                quantities = [quantity] * len(self)
                partners = [partner] * len(self)
                prices = pricelist.get_products_price(self, quantities, partners)

        for product in self:
            product.price = prices.get(product.id, 0.0)

    def _set_product_price(self):
        for product in self:
            if self._context.get('uom'):
                value = self.env['uom.uom'].browse(self._context['uom'])._compute_price(product.price, product.uom_id)
            else:
                value = product.price
            value -= product.price_extra
            product.write({'list_price': value})