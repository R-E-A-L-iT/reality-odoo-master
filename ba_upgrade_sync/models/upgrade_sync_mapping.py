# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class UpgradeSyncMapping(models.Model):
    _name = "upgrade.sync.mapping"
    _description = "Upgrade Sync Record Mapping (Odoo 17 -> Odoo 19)"
    _order = "write_date desc, id desc"
    _rec_name = "source_name"

    source_model = fields.Char("Odoo 17 Model", required=True, index=True)
    source_id = fields.Integer("Odoo 17 ID", required=True, index=True)
    source_name = fields.Char("Odoo 17 Record")
    target_model = fields.Char("Odoo 19 Model", required=True)
    target_id = fields.Integer("Odoo 19 ID", required=True, index=True)
    target_display = fields.Char("Odoo 19 Record", compute="_compute_target_display")
    match_method = fields.Selection([
        ("seed_id", "Same id (fingerprint checked)"),
        ("business_key", "Business key"),
        ("created", "Created by sync"),
        ("created_from_ref", "Created from reference"),
        ("manual", "Manual"),
    ], required=True, default="manual")

    _source_uniq = models.Constraint(
        "unique(source_model, source_id)", "An Odoo 17 record can only be mapped once.")

    @api.depends("target_model", "target_id")
    def _compute_target_display(self):
        for mapping in self:
            record = mapping._get_target()
            mapping.target_display = record.display_name if record else _("(missing)")

    def _get_target(self):
        self.ensure_one()
        if self.target_model not in self.env:
            return None
        return self.env[self.target_model].sudo().with_context(active_test=False).browse(self.target_id).exists()

    @api.model
    def _lookup(self, source_model, source_id):
        mapping = self.sudo().search([("source_model", "=", source_model), ("source_id", "=", source_id)], limit=1)
        if not mapping:
            return None
        record = mapping._get_target()
        if not record:
            # target deleted in Odoo 19: forget the stale mapping
            mapping.unlink()
            return None
        return record

    @api.model
    def _set(self, source_model, source_id, record, method, source_name=None):
        mapping = self.sudo().search([("source_model", "=", source_model), ("source_id", "=", source_id)], limit=1)
        vals = {
            "target_model": record._name,
            "target_id": record.id,
            "match_method": method,
        }
        if source_name:
            vals["source_name"] = source_name
        if mapping:
            mapping.write(vals)
        else:
            vals.update({"source_model": source_model, "source_id": source_id})
            mapping = self.sudo().create(vals)
        return mapping

    def action_open_target(self):
        self.ensure_one()
        if not self._get_target():
            raise UserError(_("The Odoo 19 record no longer exists."))
        return {
            "type": "ir.actions.act_window",
            "res_model": self.target_model,
            "res_id": self.target_id,
            "view_mode": "form",
            "target": "current",
        }
