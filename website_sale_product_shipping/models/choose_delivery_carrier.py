from odoo import api, models


class ChooseDeliveryCarrier(models.TransientModel):
    _inherit = 'choose.delivery.carrier'

    @api.depends('partner_id', 'order_id')
    def _compute_available_carrier(self):
        for rec in self:
            if rec.order_id:
                rec.available_carrier_ids = rec.order_id._get_backend_delivery_methods()
            else:
                super(ChooseDeliveryCarrier, rec)._compute_available_carrier()
