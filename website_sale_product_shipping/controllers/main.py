from odoo import http
from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleProductShipping(WebsiteSale):

    def _get_shop_payment_values(self, order, **kwargs):
        values = super()._get_shop_payment_values(order, **kwargs)

        if http.request.website.enabled_delivery:
            has_shippable = order._has_shippable_products()
            has_non_shippable = order._has_non_shippable_products()

            # Correct the storable flag: no_shipping products must not count
            values['delivery_has_storable'] = has_shippable
            values['has_non_shippable_products'] = has_non_shippable

            # Remove deliveries when there is nothing physical to ship
            if not has_shippable:
                values.pop('deliveries', None)

            # Per-product delivery selection data
            values['per_product_delivery_info'] = order._get_per_product_delivery_info()

        return values

    def order_2_return_dict(self, order):
        # Base method does delivery_line.price_unit which crashes when there
        # are multiple per-product delivery lines. Build the dict directly.
        tracking_cart_dict = {
            'transaction_id': order.id,
            'affiliation': order.company_id.name,
            'value': order.amount_total,
            'tax': order.amount_tax,
            'currency': order.currency_id.name,
            'items': self.order_lines_2_google_api(order.order_line),
        }
        delivery_lines = order.order_line.filtered('is_delivery')
        if delivery_lines:
            tracking_cart_dict['shipping'] = sum(delivery_lines.mapped('price_unit'))
        return tracking_cart_dict
