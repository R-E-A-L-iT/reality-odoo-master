# models/product_pricing.py
from odoo import api, models

class ProductPricing(models.Model):
    _inherit = "product.pricing"

    @api.model
    def _get_price(self, duration_value, duration_unit, quantity=1.0):
        if self.recurrence_id and self.recurrence_id.code == "calculated":
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
