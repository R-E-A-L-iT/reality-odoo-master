# -*- coding: utf-8 -*-

from odoo import api, fields, models


class QuoPhoneNumber(models.Model):
    _name = "quo.phone.number"
    _description = "Quo Phone Number"
    _rec_name = "display_name"
    _order = "name, formatted_number"

    quo_id = fields.Char(string="Quo Phone Number ID", required=True, index=True)  # PNxxxx
    name = fields.Char(string="Name")
    formatted_number = fields.Char(string="Formatted Number")
    raw_number = fields.Char(string="Raw Number")
    active = fields.Boolean(default=True)

    display_name = fields.Char(compute="_compute_display_name", store=True)

    _sql_constraints = [
        ("quo_id_uniq", "unique(quo_id)", "Quo Phone Number ID must be unique."),
    ]

    @api.depends("name", "formatted_number", "quo_id")
    def _compute_display_name(self):
        for r in self:
            if r.name and r.formatted_number:
                r.display_name = f"{r.name} ({r.formatted_number})"
            elif r.formatted_number:
                r.display_name = r.formatted_number
            elif r.name:
                r.display_name = r.name
            else:
                r.display_name = r.quo_id
