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
            if picking.picking_type_id.code != 'incoming' or not picking.purchase_id:
                continue

            purchase = picking.purchase_id

            _logger.info(f"Processing picking {picking.name} for purchase {purchase.name} (ID: {purchase.id})")

            serial_map = purchase.bundle_serial_data or {}
            if not serial_map:
                continue

            # Find all bundle instances by serial+bundle ID
            section_lines = purchase.order_line.filtered(lambda l: l.display_type == 'line_section' and l.name.startswith('#bundle+'))

            bundle_map = {}  # {section_line_id: bundle_instance}

            for section in section_lines:

                _logger.info(f"Bundle section found for {purchase.name} (ID: {purchase.id})... {str(section.name)})")

                serial = serial_map.get(str(section.id))
                if not serial:
                    continue
                try:
                    bundle_id = int(section.name.split('+')[-1])
                except ValueError:
                    continue

                instance = self.env['product.bundle.instance'].search([
                    ('name', '=', serial),
                    ('bundle_id', '=', bundle_id),
                ], limit=1)

                if instance:
                    _logger.info(f"Bundle instance found for {str(section.name)}: {instance.name} (ID: {instance.id})")
                    bundle_map[section.id] = instance

            if not bundle_map:
                continue

            # Map each move line to the correct bundle
            for move_line in picking.move_line_ids:
                lot = move_line.lot_id
                move = move_line.move_id
                product_line = move.purchase_line_id

                _logger.info(f"MoveLine {move_line.id} - Product: {move.product_id.display_name}, Lot: {lot and lot.name}, Purchase Line: {product_line and product_line.name}")

                if not lot:
                    _logger.warning(f"No lot found for MoveLine {move_line.id}")
                    continue
                if not product_line:
                    _logger.warning(f"No purchase_line_id found for Move {move.id}")
                    continue

                # Find closest section
                closest_section = None
                for section in section_lines:
                    if section.sequence < product_line.sequence:
                        closest_section = section

                if closest_section and closest_section.id in bundle_map:
                    bundle_instance = bundle_map[closest_section.id]
                    lot.bundle_instance_id = bundle_instance.id
                    _logger.info(f"Lot {lot.name} assigned to bundle instance {bundle_instance.name} (ID: {bundle_instance.id})")
                else:
                    _logger.warning(f"Could not find matching bundle section for product line {product_line.name} (sequence {product_line.sequence})")

        return res

