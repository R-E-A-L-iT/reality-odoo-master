# -*- coding: utf-8 -*-

from odoo import api, fields, models


class MaintenanceEquipment(models.Model):
    _inherit = "maintenance.equipment"

    equipment_assign_to = fields.Selection(
        selection_add=[("company", "Company")],
        ondelete={"company": "set default"},
    )

    owning_company_id = fields.Many2one(
        "res.partner",
        string="Owning Company",
        domain="[('is_company', '=', True)]",
        help="Company that owns or uses this equipment when 'Used By' is set to Company.",
    )

    firmware_version = fields.Char(
        string="Firmware Version",
    )

    @api.onchange("equipment_assign_to")
    def _onchange_equipment_assign_to_clear_owning_company(self):
        for record in self:
            if record.equipment_assign_to != "company":
                record.owning_company_id = False
