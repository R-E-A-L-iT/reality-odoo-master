from odoo import models, fields

class ProductBundleWizard(models.TransientModel):
    _name = 'product.bundle.wizard'
    _description = 'Product Bundle Wizard'

    bundle_id = fields.Many2one('product.bundle', string='Bundle to Add', required=True)

    def action_add_bundle_to_quote(self):
        sale_order = self.env['sale.order'].browse(self.env.context.get('active_id'))

        # Determine bundle price based on pricelist and rental status
        currency = sale_order.pricelist_id.currency_id
        is_rental = sale_order.is_rental

        if is_rental:
            price = self.bundle_id.rental_price_usd if currency.name == 'USD' else self.bundle_id.rental_price_cad
        else:
            price = self.bundle_id.price_usd if currency.name == 'USD' else self.bundle_id.price_cad

        # Construct section title with prefix, bundle name, and id
        section_title = f"#bundle+{self.bundle_id.name}+{self.bundle_id.id}"

        # Add the bundle section line
        section_line = sale_order.order_line.create({
            'order_id': sale_order.id,
            'display_type': 'line_section',
            'name': section_title,
        })

        # Add a dummy pricing line with no product just to hold the bundle price
        # sale_order.order_line.create({
        #     'order_id': sale_order.id,
        #     'product_id': line.product_id.id
        #     'name': f"{self.bundle_id.name} (bundle total)",
        #     'product_uom_qty': 1,
        #     'price_unit': price,
        #     'sequence': section_line.sequence + 1,
        # })

        # Add the actual product lines
        for line in self.bundle_id.product_lines:
            sale_order.order_line.create({
                'order_id': sale_order.id,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'name': line.product_id.name,
            })

        return {'type': 'ir.actions.act_window_close'}


