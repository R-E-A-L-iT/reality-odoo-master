from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomerPortalProduct(CustomerPortal):

    @http.route(['/my/products'], type='http', auth="user", website=True)
    def portal_my_products(self, **kwargs):
        partner = request.env.user.partner_id

        # All companies we should match: portal_companies_ids + parent_id
        partner_companies = partner.portal_companies_ids | partner.parent_id

        # Find products owned by those companies
        products = request.env['res.partner'].browse(partner_companies.ids).mapped('products')

        values = self._prepare_portal_layout_values()
        values.update({
            'products': products,
            'page_name': 'products',
        })
        return request.render("proportal.portal_my_products", values)
