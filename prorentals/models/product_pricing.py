# models/product_pricing.py
from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

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

    # Add rental_start_date and rental_stop_date if not already present
    rental_start_date = fields.Datetime()
    rental_stop_date = fields.Datetime()

    # ---------------------------------------------------------
    # Helper called from SaleOrder.action_update_rental_prices
    # ---------------------------------------------------------
    def _apply_calculated_pricing(self):
        for line in self:
            if (
                not line.product_id
                or not line.rental_start_date
                or not line.rental_stop_date
                or not line.product_id.can_be_rented
            ):
                continue

            # Detect custom recurrence by NAME; switch to XML‑ID if preferred
            recurrence = line.recurrence_id or line.product_id._get_default_rental_recurrence()
            if not recurrence or recurrence.name.lower().strip() != "calculated":
                continue  # Not our custom rule

            # Find the pricing line that uses this recurrence
            pricing = line.product_id.rental_pricing_ids.filtered(
                lambda p: p.recurrence_id and p.recurrence_id.name.lower().strip() == "calculated"
            )[:1]
            if not pricing:
                _logger.warning("Product %s has no 'Calculated' pricing line", line.product_id.display_name)
                continue

            base_rate = pricing.price  # user enters this in Rental Prices tab
            rental_days = (line.rental_stop_date - line.rental_start_date).days
            if rental_days <= 0:
                continue

            # --- Custom formula: 4‑paid / 3‑free, capped at 12 paid days ----
            full_weeks = rental_days // 7
            extra_days = rental_days % 7

            paid_days = full_weeks * 4 + min(extra_days, 4)
            paid_days = min(paid_days, 12)
            # ----------------------------------------------------------------

            line.price_unit = base_rate * paid_days
            line.discount = 0.0

            _logger.info(
                "[Calculated] %s days → %s paid days → price_unit %.2f",
                rental_days,
                paid_days,
                line.price_unit,
            )

class SaleOrder(models.Model):
    _inherit = "sale.order"

    # This is the method tied to the *Update Rental Prices* button in Odoo 17
    def action_update_rental_prices(self):
        # Let Odoo compute its standard rental prices first
        res = super().action_update_rental_prices()

        # Now apply our custom formula where relevant
        for order in self:
            order.order_line._apply_calculated_pricing()
        return res
