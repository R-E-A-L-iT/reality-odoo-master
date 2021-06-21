from odoo import models, fields

class NewModel(models.Model):

    _inherit = 'res.partner'
    
    custom_field = fields.Char(string="custom field")
