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
