# your_module/controllers/portal_sale.py
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):

    def _get_orders_domain(self, partner):
        domain = super()._get_orders_domain(partner)
        return ['|'] + domain + [('message_partner_ids', 'in', [partner.id])]
