from odoo import http
from odoo.http import request
from odoo.addons.website_sale.controllers.delivery import Delivery


class WebsiteSalePerProductDelivery(http.Controller):

    @http.route('/shop/update_carrier_for_line', type='json',
                auth='public', website=True, sitemap=False)
    def update_carrier_for_line(self, line_id, carrier_id, **kwargs):
        order = request.cart
        if not order:
            return {'success': False, 'error': 'No active order'}

        line = order.order_line.filtered(lambda l: l.id == int(line_id))
        if not line:
            return {'success': False, 'error': 'Order line not found'}

        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))
        if not carrier.exists():
            return {'success': False, 'error': 'Carrier not found'}

        # Save the customer's carrier choice on the product line
        line.sudo().write({'carrier_id': carrier.id})

        # Rebuild grouped delivery lines for the whole order (use same sudo env)
        order_sudo = order.sudo()
        order_sudo._rebuild_delivery_lines()
        order_sudo.invalidate_recordset()
        return {
            'success': True,
            'delivery_amount': order_sudo.amount_delivery,
            'order_amount_total': order_sudo.amount_total,
        }

    @http.route('/shop/rate_carrier_for_line', type='json',
                auth='public', website=True, sitemap=False)
    def rate_carrier_for_line(self, line_id, carrier_id, **kwargs):
        order = request.cart
        if not order:
            return {'success': False, 'price': 0}

        line = order.order_line.filtered(lambda l: l.id == int(line_id))
        carrier = request.env['delivery.carrier'].sudo().browse(int(carrier_id))

        if not line or not carrier.exists():
            return {'success': False, 'price': 0}

        weight = (line.product_id.weight or 0.0) * line.product_uom_qty
        rate = carrier.sudo().with_context(order_weight=weight).rate_shipment(order)

        return {
            'success': rate.get('success', False),
            'price': rate.get('price', 0),
            'carrier_price': rate.get('carrier_price', rate.get('price', 0)),
            'error_message': rate.get('error_message'),
            'warning_message': rate.get('warning_message'),
        }


class WebsiteSaleProductShippingDelivery(Delivery):

    def _get_additional_delivery_context(self):
        values = super()._get_additional_delivery_context()
        order = request.cart
        if order and order._get_shippable_lines():
            values['per_product_delivery_info'] = order._get_per_product_delivery_info()
            values['has_non_shippable_products'] = order._has_non_shippable_products()
        return values
