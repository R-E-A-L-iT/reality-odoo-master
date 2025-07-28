from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):

    def _prepare_portal_layout_values(self):
        values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        company_ids = partner.portal_companies_ids.ids
        if partner.parent_id:
            company_ids.append(partner.parent_id.id)

        product_count = request.env['product.instance'].sudo().search_count([
            ('owner', 'in', company_ids)
        ])
        values['product_count'] = product_count
        return values


