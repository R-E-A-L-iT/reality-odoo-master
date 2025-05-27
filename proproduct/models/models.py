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

class AccountMove(models.Model):
    _inherit = 'account.move'

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

