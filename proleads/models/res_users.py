from odoo import api, fields, models

class ResUsers(models.Model):
    _inherit = "res.users"

    leica_lead_reminder = fields.Boolean(
        string="Remind me to log leads with Leica",
        default=False,
        help="If enabled, you’ll get an email reminder each time you create a new Lead/Opportunity."
    )