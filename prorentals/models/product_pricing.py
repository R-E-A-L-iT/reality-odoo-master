# models/product_pricing.py
from odoo import models, api, fields
import logging

_logger = logging.getLogger(__name__)

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    # ---------------------------------------------------------
    # Helper called from SaleOrder.action_update_rental_prices
    # Adds extensive DEBUG logs so we can see why a line is kept
    # or skipped and which values are used in the formula.
    # ---------------------------------------------------------
    @api.depends('product_uom_qty', 'selected', 'discount', 'price_unit', 'tax_id')
    def _compute_amount(self):

        for line in self:
            _logger.debug("[CalDebug] Line %s: product=%s", line.id, line.product_id.display_name if line.product_id else None)

            start = getattr(line, "rental_start_date", None)
            stop = getattr(line, "rental_stop_date", None)

            if not line.product_id or not start or not stop:
                _logger.debug("[CalDebug] Skip – missing product or dates")
                continue

            if not getattr(line.product_id, "can_be_rented", False):
                _logger.debug("[CalDebug] Skip – product not rentable")
                continue

            recurrence = line.recurrence_id or getattr(line.product_id, "_get_default_rental_recurrence", lambda: None)()
            _logger.debug("[CalDebug] Recurrence: %s", recurrence.name if recurrence else None)

            if not recurrence or recurrence.name.lower().strip() != "calculated":
                _logger.debug("[CalDebug] Skip – recurrence is not 'Calculated'")
                continue

            pricing_line = line.product_id.rental_pricing_ids.filtered(
                lambda p: p.recurrence_id and p.recurrence_id.name.lower().strip() == "calculated"
            )[:1]

            if not pricing_line:
                _logger.warning("[CalDebug] Product %s has no 'Calculated' pricing line", line.product_id.display_name)
                continue

            base_rate = pricing_line.price
            rental_days = (stop - start).days
            _logger.debug("[CalDebug] Rental days: %s, Base rate: %s", rental_days, base_rate)

            if rental_days <= 0:
                _logger.debug("[CalDebug] Skip – rental_days <= 0")
                continue

            full_weeks = rental_days // 7
            extra_days = rental_days % 7
            paid_days = full_weeks * 4 + min(extra_days, 4)
            paid_days = min(paid_days, 12)

            _logger.debug("[CalDebug] full_weeks=%s, extra_days=%s, paid_days=%s", full_weeks, extra_days, paid_days)

            line.price_unit = base_rate * paid_days
            line.discount = 0.0

            _logger.info("[Calculated] %s days → %s paid → price_unit %.2f on line %s", rental_days, paid_days, line.price_unit, line.id)


# class SaleOrder(models.Model):
#     _inherit = "sale.order"

#     # Override tied to the *Update Rental Prices* button
#     def action_update_rental_prices(self):
#         _logger.debug("[CalDebug] action_update_rental_prices called for orders: %s", self.ids)
#         res = super().action_update_rental_prices()
#         for order in self:
#             _logger.debug("[CalDebug] Applying custom pricing on order %s", order.name)
#             order.order_line._apply_calculated_pricing()
#         return res