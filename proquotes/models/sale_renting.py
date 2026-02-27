# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    use_default_rental_price = fields.Boolean(
        string="Default Odoo Rental Price",
        default=True,
        help="Use the rental pricing periods/rates already defined on this product.",
    )
    use_custom_rental_price = fields.Boolean(
        string="Custom Rental Price",
        default=False,
        help="Apply the custom pricing formula (4 paid days per week, capped at 12 for the first 30 days, then linear).",
    )

    @api.onchange('use_default_rental_price')
    def _onchange_use_default_rental_price(self):
        if self.use_default_rental_price:
            self.use_custom_rental_price = False

    @api.onchange('use_custom_rental_price')
    def _onchange_use_custom_rental_price(self):
        if self.use_custom_rental_price:
            self.use_default_rental_price = False


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_pricelist_price(self):
        """Override to apply custom rental pricing formula when enabled on the product."""
        self.ensure_one()
        if self.is_rental and self.product_id.product_tmpl_id.use_custom_rental_price:
            daily_price = self.product_id.lst_price
            start_date = self.order_id.rental_start_date
            return_date = self.order_id.rental_return_date
            if start_date and return_date:
                days = (return_date - start_date).days
                return self._compute_custom_rental_price(daily_price, days)
            return daily_price
        return super()._get_pricelist_price()

    @staticmethod
    def _compute_custom_rental_price(daily_price, days):
        """Custom rental pricing formula.

        Charges 4 days per week (up to 12 days max) for the first 30 days,
        then linearly for each additional day beyond 30.

        :param float daily_price: product list price (daily rate)
        :param int days: total rental duration in days
        :return float: total rental price
        """
        if days <= 0:
            return 0
        if days <= 30:
            full_weeks = days // 7
            remaining_days = days % 7
            paid_days = 4 * full_weeks + min(remaining_days, 4)
            paid_days = min(paid_days, 12)
        else:
            paid_days = 12 + (days - 30)
        return daily_price * paid_days
