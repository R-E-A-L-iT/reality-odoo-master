from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)
_logger.info("✅ Loaded custom sale_order.py module")

class StockLot(models.Model):
    _inherit = 'stock.lot'

    bundle_instance_id = fields.Many2one(
        'product.bundle.instance',
        string="Bundle Instance",
        help="Optional link to a product bundle instance"
    )

# class AccountMove(models.Model):
#     _inherit = 'account.move'

#     def action_open_bundle_wizard(self):
#         return {
#             'type': 'ir.actions.act_window',
#             'res_model': 'product.bundle.wizard',
#             'view_mode': 'form',
#             'target': 'new',
#             'context': {
#                 'default_model': self._name,
#                 'default_res_id': self.id,
#             }
#         }

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    bundle_serial_data = fields.Json(string="Bundle Serial Cache")

    def action_open_bundle_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.bundle.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_model': self._name,
                'default_res_id': self.id,
            }
        }

    def button_confirm(self):
        for order in self:
            bundle_sections = order.order_line.filtered(
                lambda l: l.display_type == 'line_section' and l.name.startswith('#bundle+')
            )
            if bundle_sections and not order.bundle_serial_data:
                wizard = self.env['bundle.receipt.wizard'].create({
                    'order_id': order.id,
                    'serial_lines': [(0, 0, {
                        'section_line_id': section.id,
                    }) for section in bundle_sections]
                })
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'bundle.receipt.wizard',
                    'view_mode': 'form',
                    'res_id': wizard.id,
                    'target': 'new'
                }

        return super().button_confirm()

    def _confirm_after_serials(self):
        return super().button_confirm()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        res = super().button_validate()

        for picking in self:
            if picking.picking_type_id.code != 'incoming':
                continue

            purchase = picking.purchase_id
            if not purchase or not purchase.bundle_serial_data:
                continue

            # Identify bundle sections from the PO
            bundle_sections = purchase.order_line.filtered(
                lambda l: l.display_type == 'line_section' and l.name.startswith('#bundle+')
            )

            # Map section sequence to bundle_instance
            instance_map = {}
            for line in bundle_sections:
                serial = purchase.bundle_serial_data.get(str(line.id))
                if not serial:
                    continue
                instance = self.env['product.bundle.instance'].search([
                    ('name', '=', serial),
                    ('bundle_id', '=', int(line.name.split('+')[-1])),
                ], limit=1)
                if instance:
                    instance_map[line.sequence] = instance

            if not instance_map:
                continue

            # For each move line: assign bundle_instance_id on related lot
            for move_line in picking.move_line_ids:
                lot = move_line.lot_id
                if not lot:
                    continue

                product_line = move_line.move_id.purchase_line_id
                if not product_line:
                    continue

                # Find the closest previous bundle section
                section_seq = max((seq for seq in instance_map if seq < product_line.sequence), default=None)
                if section_seq:
                    lot.bundle_instance_id = instance_map[section_seq].id

        return res

