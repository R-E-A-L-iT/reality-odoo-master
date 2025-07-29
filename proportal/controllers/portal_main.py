from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self):
        values = super()._prepare_home_portal_values(counters)
        partner = request.env.user.partner_id
        company_ids = partner.portal_companies_ids.ids

        if partner.parent_id:
            company_ids.append(partner.parent_id.id)

        StockLot = request.env['stock.lot']
        if 'product_count' in counters:
            values['product_count'] = StockLot.search_count(self._prepare_quotations_domain(partner)) \
                if StockLot.check_access_rights('read', raise_exception=False) else 0

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

