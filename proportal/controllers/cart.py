# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import binascii
import logging

from odoo import fields, http, _
from odoo.exceptions import AccessError, MissingError, UserError
from odoo.http import request
from odoo.addons.portal.controllers.mail import _message_post_helper
from odoo.addons.portal.controllers.portal import CustomerPortal as CP
from odoo.addons.portal.controllers.portal import (
    pager as portal_pager,
    get_records_pager,
)
from odoo.osv import expression

_logger = logging.getLogger(__name__)


class CustomerCart(CP):
    @http.route(
        ["/shop/add-to-cart", "/shop/add-to-cart/<int:sku>"],
        type="http",
        auth="public",
        website=True,
    )
    def add_to_cart(self, sku):
        # Add item to cart based on product SKU
        qty = 1
        _logger.info("Add To Cart: " + str(sku))
        cr, uid, context, registry = (
            request.cr,
            request.uid,
            request.context,
            request.registry,
        )

        # Check user input
        try:
            product_id = (
                request.env["product.product"].sudo().search([("sku", "=", sku)])[0]
            )
        except:
            product_id = None
        _logger.info(product_id)

        # Is the product ok
        if product_id and product_id.sale_ok and product_id.website_published:
            # Get the cart-sale-order
            so = request.website.sale_get_order(force_create=1)
            # Update the cart
            so._cart_update(product_id=product_id.id, add_qty=qty)

            # Redirect to cart anyway
            return request.redirect("/shop/cart")
