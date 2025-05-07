from odoo import models, fields

class ProductBundleWizard(models.TransientModel):
    _name = 'product.bundle.wizard'
    _description = 'Product Bundle Wizard'

    bundle_id = fields.Many2one('product.bundle', string='Bundle to Add', required=True)

    def action_add_bundle_to_quote(self):
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))

        # Add a section line to indicate the bundle
        sale_order.order_line.create({
            'order_id': sale_order.id,
            'display_type': 'line_section',
            'name': f"#bundle+{self.bundle_id.name}",
        })

        # Add each product in the bundle
        for line in self.bundle_id.product_lines:
            sale_order.order_line.create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'name': line.product_id.name,
            })

        return {'type': 'ir.actions.act_window_close'}
