# -*- coding: utf-8 -*-

from odoo import models


# Product Hover Product ID Remove Functionality 
class ProductProductInherit(models.Model):
    _inherit = "product.product"

    def _compute_product_website_url(self):
        res = super(ProductProductInherit, self)._compute_product_website_url()
        for product in self:
            attributes = ','.join(str(x) for x in product.product_template_attribute_value_ids.ids)
            if attributes:
                product.website_url = "%s#attr=%s" % (product.product_tmpl_id.website_url, attributes)
            else:
                product.website_url = product.product_tmpl_id.website_url
        return res
