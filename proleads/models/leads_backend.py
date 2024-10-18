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
    
    phase1_salesperson = fields.Many2one('res.users', string="Salesperson (Logged Opportunity)")
    phase2_salesperson = fields.Many2one('res.users', string="Salesperson (Meeting)")
    phase3_salesperson = fields.Many2one('res.users', string="Salesperson (Demo)")
    phase4_salesperson = fields.Many2one('res.users', string="Salesperson (Sale)")