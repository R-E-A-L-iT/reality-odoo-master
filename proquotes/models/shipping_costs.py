from odoo import models, fields

class shipping_costs(models.Model):
    _name = "proquotes.shipping_costs"
    
    # name of package
    package_name = fields.Char("Package Name")
    # item in package
    items = fields.Many2one("product.product", string="Items")
    # warehouse location
    warehouse_location = fields.Many2one("stock.warehouse", string="Warehouse Location")
    # delivery location
    delivery_location = fields.Many2one("res.partner", string="Delivery Location")
    
    _columns = {
        'package_name': package_name,
        'items': items,
        'warehouse_location': warehouse_location,
        'delivery_location': delivery_location,
    }

    # get rate button [todo]