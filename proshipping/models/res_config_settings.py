# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    envio_base_url = fields.Char(string="Envio API Base URL", config_parameter="envio_connector.base_url")
    envio_api_token = fields.Char(string="Envio API Token/Key", config_parameter="envio_connector.api_token")
    envio_header_mode = fields.Selection(
        [
            ("bearer", "Authorization: Bearer <token>"),
            ("authorization", "Authorization: <token>"),
            ("x_api_key", "X-API-Key: <token>"),
        ],
        string="Envio Auth Header Mode",
        default="bearer",
        config_parameter="envio_connector.header_mode",
    )

    envio_devices_path = fields.Char(
        string="Devices Endpoint Path",
        default="/api/v1/devices",
        config_parameter="envio_connector.devices_path",
    )
