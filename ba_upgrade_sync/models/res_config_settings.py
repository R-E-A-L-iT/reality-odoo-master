# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    upgrade_sync_enabled = fields.Boolean(
        "Capture business events for the Odoo 19 upgrade test",
        config_parameter="ba_upgrade_sync.enabled",
    )
    upgrade_sync_event_types = fields.Char(
        "Captured event types",
        config_parameter="ba_upgrade_sync.event_types",
        help="Comma-separated event types (e.g. sale.upsert,sale.confirm). "
             "Leave empty to capture every supported type.",
    )
