from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    proleads_leica_webhook_url = fields.Char(
        string="Leica Runner Webhook URL",
        config_parameter="proleads_leica_webhook_url",
        help="URL of the machine running the Leica lead-registration script, "
             "e.g. https://runner.example.com/leica/register-lead",
    )
    proleads_leica_webhook_secret = fields.Char(
        string="Leica Runner Webhook Secret",
        config_parameter="proleads_leica_webhook_secret",
        help="Shared secret used to HMAC-sign webhook payloads. Must match the "
             "LEICA_RUNNER_SECRET configured on the runner machine.",
    )
    proleads_leica_webhook_timeout = fields.Integer(
        string="Leica Runner Timeout (seconds)",
        config_parameter="proleads_leica_webhook_timeout",
        default=120,
        help="How long Odoo waits for the runner to finish filling and submitting "
             "the portal form before giving up.",
    )
    proleads_leica_ca_username = fields.Char(
        string="Leica Portal Username (Canada)",
        config_parameter="proleads_leica_ca_username",
    )
    proleads_leica_ca_password = fields.Char(
        string="Leica Portal Password (Canada)",
        config_parameter="proleads_leica_ca_password",
    )
    proleads_leica_us_username = fields.Char(
        string="Leica Portal Username (United States)",
        config_parameter="proleads_leica_us_username",
    )
    proleads_leica_us_password = fields.Char(
        string="Leica Portal Password (United States)",
        config_parameter="proleads_leica_us_password",
    )
