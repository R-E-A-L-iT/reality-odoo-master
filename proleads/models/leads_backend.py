from odoo import fields, models, api, tools

class opportunity(models.Model):
    _inherit = 'crm.lead'

    opportunity_source = fields.Selection([
        ("source_website", "Website"),
        ("source_landing", "Landing Page"),
        ("source_linkedin", "LinkedIn"),
        ("source_social", "Other Social Platforms"),
        ("source_email", "Email Campaign"),
        ("source_trade", "Tradeshow"),
        ("source_other", "Other Source"),
        ],
        string="Opportunity Source")
    
    phase1_salesperson = fields.Many2one('res.users', string="Salesperson [Optional]")
    phase2_salesperson = fields.Many2one('res.users', string="Salesperson [Optional]")
    phase3_salesperson = fields.Many2one('res.users', string="Salesperson [Optional]")
    phase4_salesperson = fields.Many2one('res.users', string="Salesperson [Optional]")
    phase5_salesperson = fields.Many2one('res.users', string="Salesperson [Optional]")