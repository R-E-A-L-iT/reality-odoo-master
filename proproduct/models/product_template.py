# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)

class ProductTemplate(models.Model):
    _inherit = "product.template"

    approve_financing = fields.Boolean("Approve Financing", default=False, help="If checked, the eCommerce page will show an APPROVE financing section.")
    show_add_to_cart = fields.Boolean("Show Add to Cart Button", default=False, help="If checked, the eCommerce page will show an Add To Cart button.")
    rental_behaviour_on_store = fields.Boolean(
        string="Rental behaviour on store",
        default=False,
        help="If enabled, rental-specific elements will be shown on the website product page."
    )

    is_us = fields.Boolean(string='Is Published in US')
    is_ca = fields.Boolean(string='Is Published in CA')

    def _proproduct_resolve_pricelist_item(self, pricelist, variant):
        """Return the most-specific pricelist item applicable to *variant*.

        Worked around because Odoo's own `_get_applicable_rules` /
        `_get_product_price` fail to return a valid item on very large pricelists
        (observed: 10k+ items make `_get_product_price_rule` return (list_price,
        False) even though a matching fixed rule exists).

        Uses the exact sudo `item_ids.filtered` approach the template uses (proven
        to find the rule), restricted to variant/product rules — no search domain,
        no `parent_of` (which raises on category-less products), so it can't be
        swallowed by the try/except in the caller.
        """
        if not pricelist:
            return self.env['product.pricelist.item']
        items = pricelist.sudo().item_ids.filtered(
            lambda i: (i.applied_on == '0_product_variant' and i.product_id.id == variant.id)
            or (i.applied_on == '1_product' and i.product_tmpl_id.id == variant.product_tmpl_id.id)
        )
        if not items:
            return self.env['product.pricelist.item']
        return items.sorted(key=lambda i: 0 if i.applied_on == '0_product_variant' else 1)[:1]

    def _get_combination_info(self, *args, **kwargs):
        """Force the storefront price to the pricelist rule actually applicable to
        the current pricelist (cookie/geo-resolved), computed ourselves.

        This fixes two things at once:
          * Odoo dropping valid rules on huge pricelists (see resolver above), and
          * rental (`rent_ok`) products whose displayed price is overridden to the
            rental price — for these we show the regular sales price instead
            (unless the product is explicitly flagged `rental_behaviour_on_store`).
        """
        info = super()._get_combination_info(*args, **kwargs)
        if not request:
            return info
        try:
            variant = self.env['product.product'].browse(info.get('product_id')).exists() \
                or self.product_variant_id
            pricelist = self.env['website'].get_current_pricelist()
            item = self._proproduct_resolve_pricelist_item(pricelist, variant)
            if item:
                if item.compute_price == 'fixed':
                    price = item.fixed_price            # already in pricelist currency
                else:
                    price = item._compute_price(
                        variant, 1.0, variant.uom_id,
                        fields.Date.context_today(self), pricelist.currency_id,
                    )
                _logger.info(
                    "[proproduct] storefront price for %s on %s -> %s (rule %s, was %s)",
                    variant.display_name, pricelist.display_name, price, item.id, info.get('price'),
                )
                info['price'] = price
                info['list_price'] = price
                info['has_discounted_price'] = False
                if info.get('is_rental') and not self.rental_behaviour_on_store:
                    info['is_rental'] = False
        except Exception as e:
            _logger.warning("[proproduct] storefront price override failed: %s", e)
        return info

    def action_is_us_toggle(self):
        self.is_us = not self.is_us

    def action_is_ca_toggle(self):
        self.is_ca = not self.is_ca
