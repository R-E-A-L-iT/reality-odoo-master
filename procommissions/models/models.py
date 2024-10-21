from odoo import models, fields

class ProCommissions(models.Model):
    _name = 'pro.commissions'
    _description = 'Commissions Records'

    name = fields.Char(string="Commission Name", required=True)
    amount = fields.Float(string="Amount")