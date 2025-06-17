# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ProductRentalPricing(models.Model):
    _inherit = "product.pricing"

    # 1)  Extend the “unit” selection with an extra value
    unit = fields.Selection(
        selection_add=[("calculated", "Calculated")],
        ondelete={"calculated": "set default"},
    )

    # 2)  A base rate to apply the formula on (same currency as product)
    #     We reuse the existing `price` field – this will be the base-day rate.
    # ----------------------------------------------------------------------
    # 3)  Override price computation so that ANY call to
    #         pricing._get_price(duration, qty)
    #     returns the calculated amount if unit == 'calculated'
    # ----------------------------------------------------------------------
    @api.model
    def _get_price(self, duration_value, duration_unit, quantity=1.0):
        """
        duration_value : float, e.g. 5
        duration_unit  : 'hour', 'day', 'week', 'month'
        quantity       : number of products being rented
        """
        if self.unit != "calculated":
            return super()._get_price(duration_value, duration_unit, quantity)

        # ---------- Convert everything to **days** ----------
        if duration_unit == "day":
            days = duration_value
        elif duration_unit == "week":
            days = duration_value * 7
        elif duration_unit == "month":
            # Rental module uses 30-day months
            days = duration_value * 30
        elif duration_unit == "hour":
            days = duration_value / 24.0
        else:
            days = duration_value  # fallback

        # ---------- Apply the formula ----------
        base = self.price                          # base-day rate set on the line
        paid_days = 0

        full_weeks = int(days // 7)                # every 7 calendar days → 4 paid
        paid_days += full_weeks * 4

        remainder = int(days % 7)                  # remaining calendar days
        paid_days += min(remainder, 4)             # pay up to 4 of them

        paid_days = min(paid_days, 12)             # 12-day cap

        total = base * paid_days * quantity        # quantity = nbr of items
        return total
