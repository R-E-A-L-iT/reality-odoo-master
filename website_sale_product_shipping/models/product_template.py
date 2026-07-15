from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    no_shipping = fields.Boolean(
        string='No Shipping Required',
        help='Enable for digital or software products that do not require physical shipping. '
             'Customers will not be prompted to select a shipping method for this product.',
    )
    allowed_carrier_ids = fields.Many2many(
        comodel_name='delivery.carrier',
        relation='product_template_delivery_carrier_rel',
        column1='product_template_id',
        column2='carrier_id',
        string='Allowed Shipping Methods',
        help='Leave empty to allow all published carriers. '
             'Select specific carriers to restrict which shipping methods '
             'are available for this product at checkout.',
    )
