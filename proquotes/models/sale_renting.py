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
			start_date = self.order_id.rental_start_date
			return_date = self.order_id.rental_return_date

			if start_date and return_date:
				days = (return_date - start_date).days
				return self._compute_custom_rental_price(daily_price, days)

			return daily_price

		return super()._get_pricelist_price()

	def _get_custom_rental_daily_price(self):
		"""Resolve the daily price for the custom rental formula.

		Priority:
		  1. Daily rule (unit='day', duration=1) matching the order's pricelist.
		  2. Daily rule (unit='day', duration=1) with no pricelist (global rule).
		  3. product.template.list_price (fallback).
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

		# 3. Fallback to list_price.
		return tmpl.list_price

	@staticmethod
	def _compute_custom_rental_price(daily_price, days):
		"""Custom rental pricing formula.

		Charges 4 days per week (up to 12 days max) for the first 30 days,
		then linearly for each additional day beyond 30.

		:param float daily_price: price per day
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
