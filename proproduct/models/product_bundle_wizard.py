from odoo import models, fields

class ProductBundleWizard(models.TransientModel):
    _name = 'product.bundle.wizard'
    _description = 'Product Bundle Wizard'

    bundle_id = fields.Many2one('product.bundle', string='Bundle to Add', required=True)

    def action_add_bundle_to_quote(self):
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))

        # Determine price based on pricelist currency
        currency = sale_order.pricelist_id.currency_id
        if currency.name == 'USD':
            price = self.bundle_id.price_usd
        else:
            price = self.bundle_id.price_cad

        # Construct section title with prefix, bundle name, and price
        section_title = f"#bundle+{self.bundle_id.name}+{self.bundle_id.id}"

        # Add section line
        sale_order.order_line.create({
            'order_id': sale_order.id,
            'display_type': 'line_section',
            'name': section_title,
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

