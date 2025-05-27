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

            # insert bundle section
            section_line = doc.order_line.create({
                'order_id': doc.id,
                'name': f"#bundle+{self.bundle_id.name}+{self.bundle_id.id}",
                'display_type': 'line_section',
                'product_uom_qty': 1,    
                'product_qty': 1,        
                'product_uom': self.bundle_id.product_lines[0].product_id.uom_po_id.id
                                if self.bundle_id.product_lines else self.env.ref('uom.product_uom_unit').id,
            }).sudo()

            # Immediately clear fields that violate the constraint
            section_line.write({
                'product_uom_qty': 0,
                'product_qty': 0,
                'product_uom': False,
                'product_id': False,
                'price_unit': 0,
            })

            # insert bundle lines
            for line in self.bundle_id.product_lines:
                doc.order_line.create({
                    'order_id': doc.id,
                    'product_id': line.product_id.product_variant_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_id.uom_po_id.id,
                    'price_unit': line.product_id.standard_price,
                    'name': line.product_id.name,
                })

class BundleReceiptWizard(models.TransientModel):
    _name = 'bundle.receipt.wizard'
    _description = 'Enter Serial Numbers for Bundles'

    order_id = fields.Many2one('purchase.order', required=True)
    serial_lines = fields.One2many('bundle.receipt.line.wizard', 'wizard_id', string='Bundle Serials')

    def action_confirm_with_serials(self):
        self.ensure_one()
        self.order_id.bundle_serial_data = {
            line.section_line_id.id: line.serial_number for line in self.serial_lines
        }
        return self.order_id._confirm_after_serials()

class BundleReceiptLineWizard(models.TransientModel):
    _name = 'bundle.receipt.line.wizard'
    _description = 'Single Bundle Product Entry'

    wizard_id = fields.Many2one('bundle.receipt.wizard', required=True)
    section_line_id = fields.Many2one('purchase.order.line', required=True)
    bundle_name = fields.Text(related='section_line_id.name', string="Bundle")
    serial_number = fields.Char(required=True, string="Serial Number")

    product_names = fields.Text(string="Bundle Products", compute='_compute_product_names')

    def _compute_product_names(self):
        for rec in self:
            rec.product_names = '\n'.join(
                rec.section_line_id.order_id.order_line.filtered(
                    lambda l: l.sequence > rec.section_line_id.sequence and not l.display_type
                ).mapped('name')
            )
