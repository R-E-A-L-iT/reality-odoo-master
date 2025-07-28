from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.exceptions import AccessError

class CustomPortalOrders(CustomerPortal):

    @http.route(['/my/orders/company/<int:order_id>/<int:partner_id>'], type='http', auth="user", website=True)
    def portal_my_order_custom(self, order_id=None, partner_id=None, **kw):
        order = request.env['sale.order'].sudo().browse(order_id)
        partner = request.env.user.partner_id

        # Only allow if the partner is the customer OR a follower
        if not order.exists() or not (
            partner.id == order.partner_id.id or
            partner.id in order.message_partner_ids.ids or
            partner.id in order.partner_id.child_ids.ids
        ):
            raise AccessError("You do not have permission to view this order.")

        return request.render("sale.portal_my_order", {
            'order': order,
            'message': False,
        })
