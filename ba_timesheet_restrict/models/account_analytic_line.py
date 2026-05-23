# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import timedelta


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    @api.constrains('date')
    def _check_timesheet_date(self):
        allowed_past_days = int(self.env['ir.config_parameter'].sudo().get_param('timesheet.allowed_past_days', 0))
        allowed_future_days = int(self.env['ir.config_parameter'].sudo().get_param('timesheet.allowed_future_days', 0))

        today = fields.Date.today()

        for record in self:
            if allowed_past_days > 0:
                min_date = today - timedelta(days=allowed_past_days)
                if record.date < min_date:
                    raise ValidationError(_(f"You can only log timesheets up to {allowed_past_days} days in the past."))

            if allowed_future_days > 0:
                max_date = today + timedelta(days=allowed_future_days)
                if record.date > max_date:
                    raise ValidationError(_(f"You can only log timesheets up to {allowed_future_days} days in the future."))
