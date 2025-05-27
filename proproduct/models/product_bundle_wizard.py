from odoo import models, fields, api

class ProductBundleWizard(models.TransientModel):
    _name = 'product.bundle.wizard'
    _description = 'Product Bundle Wizard'

    bundle_id = fields.Many2one('product.bundle', string='Bundle to Add', required=True)

    def action_add_bundle_to_document(self):
        self.ensure_one()

        active_model = self._context.get('default_model')
        active_id = self._context.get('default_res_id')
        doc = self.env[active_model].browse(active_id)

        # Insert section + sub lines based on bundle
        if active_model == 'sale.order':


            # Determine bundle price based on pricelist and rental status
            currency = sale_order.pricelist_id.currency_id
            is_rental = getattr(sale_order, 'is_rental', False)  # handle case where field may not exist

            if is_rental:
                price = self.bundle_id.rental_price_usd if currency.name == 'USD' else self.bundle_id.rental_price_cad
            else:
                price = self.bundle_id.price_usd if currency.name == 'USD' else self.bundle_id.price_cad

            # Construct section title
            section_title = f"#bundle+{self.bundle_id.name}+{self.bundle_id.id}"

            # Add the bundle section line
            section_line = sale_order.order_line.create({
                'order_id': sale_order.id,
                'display_type': 'line_section',
                'name': section_title,
            })

            # Add the bundle helper pricing line using the dummy product
            bundle_price_line = sale_order.order_line.create({
                'order_id': sale_order.id,
                'product_id': 564922,  # Dummy product ID
                'product_uom_qty': 1,
                'price_unit': price,
                'name': f"$$bundle_helper$$:{self.bundle_id.name}",
                'sequence': section_line.sequence + 1,
                'is_selected': True,
            })

            # Add actual product lines
            sequence = bundle_price_line.sequence + 1
            for line in self.bundle_id.product_lines:
                sale_order.order_line.create({
                    'order_id': sale_order.id,
                    'product_id': line.product_id.product_variant_id.id,
                    'product_uom_qty': line.quantity,
                    'name': line.product_id.name,
                    'sequence': sequence,
                    'is_selected': False,
                })
                sequence += 1

            return {'type': 'ir.actions.act_window_close'}


        # elif active_model == 'account.move':

        #     # Insert into invoice lines
        #     doc.invoice_line_ids = [(0, 0, {
        #         'name': self.bundle_id.name,
        #         'display_type': 'line_section',
        #     })]
        #     for line in self.bundle_id.product_lines:
        #         doc.invoice_line_ids += [(0, 0, {
        #             'product_id': line.product_id.id,
        #             'quantity': line.quantity,
        #             'price_unit': line.product_id.list_price,
        #             'name': line.product_id.name,
        #         })]


        elif active_model == 'purchase.order':

            # Insert into PO lines
            # doc.order_line = [(0, 0, {
            #     'name': self.bundle_id.name,
            #     'display_type': 'line_section',
            # })]
            for line in self.bundle_id.product_lines:
                doc.order_line.create({
                    'order_id': doc.id,
                    'product_id': line.product_id.product_variant_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_po_id.id,
                    'price_unit': line.product_id.standard_price,
                    'name': line.product_id.name,
                })

