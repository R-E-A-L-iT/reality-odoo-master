# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    quo_api_key = fields.Char(
        string="Quo API Key",
        config_parameter="quo_transcripts.api_key",
        help="API key used for admin import/backfill (wizard/cron).",
    )
    quo_webhook_secret = fields.Char(
        string="Quo Webhook Secret",
        config_parameter="quo_transcripts.webhook_secret",
        help="Secret used to validate the openphone-signature header.",
    )
    quo_api_base_url = fields.Char(
        string="Quo API Base URL",
        config_parameter="quo_transcripts.api_base_url",
        default="https://api.openphone.com/v1",
        help="Base URL for Quo API. Example: https://api.openphone.com/v1",
    )
