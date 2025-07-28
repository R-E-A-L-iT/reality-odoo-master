from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id

        # Count products linked to portal_companies_ids or parent
        companies = partner.portal_companies_ids | partner.parent_id
        product_count = request.env['res.partner'].browse(companies.ids).mapped('products')
        values['product_count'] = len(product_count)
        return values
