from odoo import fields, models


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    restricted_product_count = fields.Integer(
        string='Restricted Products',
        compute='_compute_restricted_product_count',
    )

    def _compute_restricted_product_count(self):
        for carrier in self:
            carrier.restricted_product_count = self.env['product.template'].search_count(
                [('allowed_carrier_ids', 'in', carrier.id)]
            )

    def action_view_restricted_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Products Restricted to This Carrier',
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('allowed_carrier_ids', 'in', self.id)],
        }

    def _get_price_available(self, order):
        """Exclude no_shipping products from weight/volume/quantity calculation."""
        self.ensure_one()
        self = self.sudo()
        order = order.sudo()
        total = weight = volume = quantity = wv = 0
        for line in order.order_line:
            if line.state == 'cancel':
                continue
            if not line.product_id or line.is_delivery:
                continue
            if line.product_id.type in {'service', 'combo'}:
                continue
            if line.product_id.no_shipping:
                continue
            qty = line.product_uom_id._compute_quantity(line.product_uom_qty, line.product_id.uom_id)
            weight += (line.product_id.weight or 0.0) * qty
            volume += (line.product_id.volume or 0.0) * qty
            wv += (line.product_id.weight or 0.0) * (line.product_id.volume or 0.0) * qty
            quantity += qty
        total = order._compute_amount_total_without_delivery()

        total = self._compute_currency(order, total, 'pricelist_to_company')
        weight = self.env.context.get('order_weight') or order.shipping_weight or weight
        return self._get_price_from_picking(total, weight, volume, quantity, wv=wv)
