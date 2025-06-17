# models/product_pricing.py
from odoo import api, models

class ProductPricing(models.Model):
    _inherit = "product.pricing"

    @api.model
    def _get_price(self, duration_value, duration_unit, quantity=1.0):
        if self.recurrence_id and self.recurrence_id.name.lower() == "calculated":

            # Convert to days
            if duration_unit == "week":
                days = duration_value * 7
            elif duration_unit == "month":
                days = duration_value * 30
            elif duration_unit == "hour":
                days = duration_value / 24
            else:
                days = duration_value

            base = self.price
            full_weeks = int(days // 7)
            paid = full_weeks * 4
            paid += min(int(days % 7), 4)
            paid = min(paid, 12)
            return base * paid * quantity

        # Fallback to standard logic
        return super()._get_price(duration_value, duration_unit, quantity)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.onchange('product_id', 'rental_start_date', 'rental_stop_date')
    def _onchange_rental_dates_override_calculated(self):
        super()._onchange_rental_dates()

        if not self.product_id or not self.rental_start_date or not self.rental_stop_date:
            return

        # Check if product has a "Calculated" recurrence pricing line
        calculated_line = self.product_id.rental_pricing_ids.filtered(
            lambda p: p.recurrence_id and p.recurrence_id.name.lower().strip() == "calculated"
        )

        if not calculated_line:
            return  # use standard Odoo logic

        # Use the first applicable calculated pricing line
        pricing = calculated_line[0]
        base_price = pricing.price

        # Calculate rental duration in days
        duration = (self.rental_stop_date - self.rental_start_date).days
        if duration <= 0:
            return

        # Apply custom "4 paid, 3 free" logic, max 12 paid days
        full_weeks = duration // 7
        extra_days = duration % 7

        paid_days = full_weeks * 4 + min(extra_days, 4)
        paid_days = min(paid_days, 12)

        self.price_unit = base_price * paid_days
        self.discount = 0.0

