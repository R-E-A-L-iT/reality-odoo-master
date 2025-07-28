from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError

class CustomPortalOrders(CustomerPortal):

    @http.route([ '/my/orders/<int:order_id>', '/my/orders/company/<int:order_id>/<int:partner_company_id>' ], type='http', auth="user", website=True)
    def portal_order_company_page(self, order_id, partner_company_id=None, **kw):
        order_sudo = request.env['sale.order'].sudo().browse(order_id)
        partner = request.env.user.partner_id

        if not order_sudo.exists() or not (
            partner.id == order_sudo.partner_id.id or
            partner.id in order_sudo.message_partner_ids.ids or
            partner.id in order_sudo.partner_id.child_ids.ids
        ):
            raise AccessError("You do not have permission to view this order.")

        values = {
            'sale_order': order_sudo,
            'partner_company_id': partner_company_id,
            'message': False,
            'bootstrap_formatting': True,
            'action': order_sudo._get_portal_return_action(),
            'report_type': 'html',
        }
        return request.render('sale.sale_order_portal_template', values)
