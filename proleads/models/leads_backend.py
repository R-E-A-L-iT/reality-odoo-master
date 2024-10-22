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
    
    phase1_salesperson = fields.Many2one('res.users', string="Salesperson [New Customer]")
    phase2_salesperson = fields.Many2one('res.users', string="Salesperson [New Lead]")
    phase3_salesperson = fields.Many2one('res.users', string="Salesperson [Developed Opportunity]")
    phase4_salesperson = fields.Many2one('res.users', string="Salesperson [Performed Demo]")
    phase5_salesperson = fields.Many2one('res.users', string="Salesperson [Quote to Order]")