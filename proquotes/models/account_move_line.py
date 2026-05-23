# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo import models, fields, api


_logger = logging.getLogger(__name__)

class invoiceLine(models.Model):
    _inherit = "account.move.line"

    x_needs_section = fields.Boolean(index=True)
    x_section_label = fields.Char()

    applied_name = fields.Char( string="Applied Name")

    price_override = fields.Boolean(default=False, string="Override Price")

    def get_price(self):
        pricelist = self.move_id.pricelist_id
        product = self.product_id
        _logger.info("Invoice Price: " + str(product.name))
        priceResult = self.env["product.pricelist.item"].search(
            [
                ("pricelist_id.id", "=", pricelist.id),
                ("product_tmpl_id.sku", "=", product.sku),
            ]
        )
        if len(priceResult) < 1:
            return product.price

        # Appy Price from Pricelist
        return priceResult[-1].fixed_price

    @api.onchange("price_unit")
    def init_price(self):
        # Set flag marking price as custom
        self.price_override = self.price_unit != self.get_price()
