from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSaleProductShipping(WebsiteSale):

    def _prepare_checkout_page_values(self, order_sudo, **kwargs):
        values = super()._prepare_checkout_page_values(order_sudo, **kwargs)
        if order_sudo._get_shippable_lines():
            values['per_product_delivery_info'] = order_sudo._get_per_product_delivery_info()
            values['has_non_shippable_products'] = order_sudo._has_non_shippable_products()
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
