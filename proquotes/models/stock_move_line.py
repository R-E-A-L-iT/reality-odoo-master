from odoo import models

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def action_open_lot_record(self):
        self.ensure_one()
        if self.lot_id:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Edit Serial/Lot',
                'view_mode': 'form',
                'res_model': 'stock.lot',
                'res_id': self.lot_id.id,
                'target': 'current',
            }