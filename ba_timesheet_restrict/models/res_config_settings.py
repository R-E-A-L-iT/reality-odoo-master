# -*- coding: utf-8 -*-

from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    timesheet_allowed_past_days = fields.Integer(
        string="Allowed Before Days for Timesheets",
        config_parameter='timesheet.allowed_past_days',
        default=0,
        help="Number of past days users can log timesheets for. Set to 0 to disallow past entries."
    )

    timesheet_allowed_future_days = fields.Integer(
        string="Allowed Future Days for Timesheets",
        config_parameter='timesheet.allowed_future_days',
        default=0,
        help="Number of future days users can log timesheets for. Set to 0 to disallow future entries."
    )
