from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self):
        values = super()._prepare_home_portal_values()
        partner = request.env.user.partner_id
        company_ids = partner.portal_companies_ids.ids
        if partner.parent_id:
            company_ids.append(partner.parent_id.id)

        product_count = request.env['stock.lot'].sudo().search_count([
            ('owner', 'in', company_ids)
        ])
        values['product_count'] = product_count
        return values

    # def _prepare_home_portal_values(self, counters):
    #     values = super()._prepare_home_portal_values(counters)
    #     partner = request.env.user.partner_id

    #     SaleOrder = request.env['sale.order']
    #     if 'quotation_count' in counters:
    #         values['quotation_count'] = SaleOrder.search_count(self._prepare_quotations_domain(partner)) \
    #             if SaleOrder.check_access_rights('read', raise_exception=False) else 0
    #     if 'order_count' in counters:
    #         values['order_count'] = SaleOrder.search_count(self._prepare_orders_domain(partner), limit=1) \
    #             if SaleOrder.check_access_rights('read', raise_exception=False) else 0

    #     return values

