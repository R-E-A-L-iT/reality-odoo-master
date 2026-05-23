# -*- coding: utf-8 -*-

from odoo import api, fields, models
import logging
from odoo import api, fields, models, _
from odoo.tools.translate import _
from odoo import models, fields, api
from odoo.tools.misc import groupby as tools_groupby


class product(models.Model):
    _inherit = "product.template"

    service_policy = [
        ('ordered_prepaid', 'Prepaid/Fixed Price'),
        ('delivered_manual', 'Based on Delivered Quantity (Manual)'),
        ('delivered_milestones', 'Based on Milestones'),
        ('delivered_timesheet', 'Based on Timesheets')
    ]

    cad_val = fields.Monetary(string="Canadian Product Value")
    usd_val = fields.Monetary(string="United States Product Value")
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

    _inherit = 'product.template'

    use_default_rental_price = fields.Boolean(
        string="Default Odoo Rental Price",
        default=False,
        help="Use the rental pricing periods/rates already defined on this product.",
    )
    use_custom_rental_price = fields.Boolean(
        string="Custom Rental Price",
        default=True,
        help="Apply the custom pricing formula (4 paid days per week, capped at 12 for the first 30 days, then linear).",
    )
