from odoo import fields, models, api


class Partner(models.Model):
    _inherit = 'res.partner'
    pricelist_id = fields.Many2one('product.pricelist', 'Pricelist_Sync')
