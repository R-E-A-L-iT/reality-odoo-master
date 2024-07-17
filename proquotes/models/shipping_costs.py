from odoo import models, fields

class shipping_costs(models.Model):
    _name = "proquotes.shipping_costs"
    
    # name of package
    package_name = fields.Char("Package Name")
    items = fields.Many2one("product.product", string="Items")