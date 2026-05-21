# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.misc import groupby as tools_groupby

# add note to allow rebase

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


class SaleOrderLine(models.Model):
	_inherit = 'sale.order.line'

	rental_daily_price = fields.Float(
		compute='_compute_rental_daily_price',
		digits='Product Price',
	)

	@api.depends('order_id.is_rental_order', 'product_id', 'order_id.pricelist_id')
	def _compute_rental_daily_price(self):
		for line in self:
			is_rental_line = line.order_id.is_rental_order and line.product_id.rent_ok
			line.rental_daily_price = line._get_custom_rental_daily_price() if is_rental_line else 0.0

	def _get_pricelist_price(self):
		"""Override to apply custom rental pricing formula when enabled on the product."""
		self.ensure_one()

		# Use order-level is_rental_order + product rent_ok instead of line.is_rental.
		# line.is_rental is stored at creation time and requires 'in_rental_app' context,
		# which is absent when lines are added via templates or other non-rental-app paths.
		is_rental_line = self.order_id.is_rental_order and self.product_id.rent_ok

		if is_rental_line and self.product_id.product_tmpl_id.use_custom_rental_price:
			daily_price = self._get_custom_rental_daily_price()
			if not daily_price:
				return super()._get_pricelist_price()
			start_date = self.order_id.rental_start_date
			return_date = self.order_id.rental_return_date

			if start_date and return_date:
				# Minimum rental is 1 day; same-day counts as 1 day.
				days = max(1, (return_date.date() - start_date.date()).days)
				return self._compute_custom_rental_price(daily_price, days)

			return daily_price

		return super()._get_pricelist_price()

	def _get_custom_rental_daily_price(self):
		"""Resolve the daily price for the custom rental formula.

		Priority:
		  1. Daily rule (unit='day', duration=1) matching the order's pricelist.
		  2. Daily rule (unit='day', duration=1) with no pricelist (global rule).
		  3. Daily rule whose pricelist has the same currency as the order pricelist.
		  4. 0.0 if no daily rule found (template falls back to Odoo's price_unit).
		"""
		self.ensure_one()
		tmpl = self.product_id.product_tmpl_id
		order_pricelist = self.order_id.pricelist_id

		daily_rules = tmpl.product_pricing_ids.filtered(
			lambda p: p.recurrence_id.unit == 'day' and p.recurrence_id.duration == 1
		)

		# 1. Match the order's pricelist exactly.
		if order_pricelist:
			matched = daily_rules.filtered(lambda p: p.pricelist_id == order_pricelist)
			if matched:
				return matched[0].price

		# 2. Global daily rule (no pricelist).
		global_rule = daily_rules.filtered(lambda p: not p.pricelist_id)
		if global_rule:
			return global_rule[0].price

		# 3. Daily rule whose pricelist shares the same currency as the order pricelist.
		#    Handles the case where the order uses a general pricelist in the same currency
		#    as a rental-specific pricelist (e.g. order uses "CAD" → matches "CAD RENTAL (CAD)").
		if order_pricelist and daily_rules:
			currency_match = daily_rules.filtered(
				lambda p: p.pricelist_id and p.pricelist_id.currency_id == order_pricelist.currency_id
			)
			if currency_match:
				return currency_match[0].price

		# 4. No daily pricing rule found — return 0 so the template falls back to
		#    Odoo's computed price_unit (the proper rental price, not the sale price).
		return 0.0

	@staticmethod
	def _compute_custom_rental_price(daily_price, days):
		if days <= 0:
			return 0

		def paid_days_for_partial_month(day_count):
			full_weeks = day_count // 7
			extra_days = day_count % 7
			return min((full_weeks * 4) + min(extra_days, 4), 12)

		full_months = days // 30
		remaining_days = days % 30

		paid_days = full_months * 12

		if remaining_days:
			paid_days += paid_days_for_partial_month(remaining_days)

		return daily_price * paid_days

	def _partition_so_lines_by_rental_period(self):
		"""Override to guard against False reservation_begin / return_date.

		When rental dates are left empty (allowed by our proquotes customisation),
		base Odoo tries max(False, now) which raises TypeError.  Fall back to
		`now` for any missing date so the groupby still runs cleanly.
		"""
		now = fields.Datetime.now()
		lines_grouping_key = {
			line.id: (line.reservation_begin or now, line.return_date or now, line.order_id.warehouse_id.id)
			for line in self
		}
		keyfunc = lambda line_id: (
			max(lines_grouping_key[line_id][0], now),
			lines_grouping_key[line_id][1],
			lines_grouping_key[line_id][2],
		)
		return tools_groupby(self._ids, key=keyfunc)
