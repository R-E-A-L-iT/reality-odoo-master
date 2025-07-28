from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomerPortalProduct(CustomerPortal):

    @http.route(['/my/products'], type='http', auth="user", website=True)
    def portal_my_products(self, **kwargs):
        partner = request.env.user.partner_id
        company_ids = partner.portal_companies_ids.ids
        if partner.parent_id:
            company_ids.append(partner.parent_id.id)

        products = request.env['stock.lot'].sudo().search([
            ('owner_id', 'in', company_ids),
        ])

        values = self._prepare_portal_layout_values()
        values.update({
            'products': products,
            'page_name': 'products',
        })
        return request.render("proportal.portal_my_products", values)
