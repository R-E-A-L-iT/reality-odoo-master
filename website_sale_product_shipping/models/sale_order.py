from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_charge_count = fields.Integer(compute='_compute_delivery_charge_info')
    delivery_charge_total = fields.Monetary(
        compute='_compute_delivery_charge_info',
        currency_field='currency_id',
    )

    @api.depends('order_line.is_delivery', 'order_line.price_total')
    def _compute_delivery_charge_info(self):
        for order in self:
            delivery_lines = order.order_line.filtered('is_delivery')
            order.delivery_charge_count = len(delivery_lines)
            order.delivery_charge_total = sum(delivery_lines.mapped('price_total'))

    def action_view_delivery_charges(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Delivery Charges',
            'res_model': 'sale.order.line',
            'view_mode': 'list,form',
            'domain': [('order_id', '=', self.id), ('is_delivery', '=', True)],
            'context': {'default_order_id': self.id},
        }

    def _compute_cart_info(self):
        super()._compute_cart_info()
        for order in self:
            # Treat no_shipping products the same as services:
            # if all lines are services or no_shipping → no carrier needed at checkout.
            order.only_services = all(
                l.product_id.type == 'service' or l.product_id.no_shipping
                for l in order.website_order_line
            )

    def _get_delivery_methods(self):
        """For e-commerce checkout: hide shipping section if only no_shipping products."""
        all_carriers = super()._get_delivery_methods()

        shippable_lines = self.order_line.filtered(
            lambda l: not l.is_delivery
            and not l.display_type
            and l.product_id.type != 'service'
            and not l.product_id.no_shipping
        )
        if not shippable_lines:
            return self.env['delivery.carrier']

        return all_carriers

    def _get_estimated_weight(self):
        """Exclude no_shipping products from shipping weight calculation."""
        self.ensure_one()
        weight = 0.0
        for line in self.order_line.filtered(
            lambda l: l.product_id.type in ['product', 'consu']
            and not l.is_delivery
            and not l.display_type
            and l.product_uom_qty > 0
            and not l.product_id.no_shipping
        ):
            weight += line.product_qty * line.product_id.weight
        return weight

    def _has_shippable_products(self):
        return any(
            line.product_id.type in ['consu', 'product']
            and not line.product_id.no_shipping
            for line in self.order_line
            if not line.is_delivery and not line.display_type
        )

    def _has_non_shippable_products(self):
        return any(
            line.product_id.no_shipping
            for line in self.order_line
            if not line.is_delivery and not line.display_type
        )

    # ── Per-product checkout delivery ──────────────────────────────────────

    def _get_shippable_lines(self):
        """Product lines that need a physical carrier selected at checkout."""
        return self.order_line.filtered(
            lambda l: not l.is_delivery
            and not l.display_type
            and l.product_id.type in ['consu', 'product']
            and not l.product_id.no_shipping
        )

    def _get_per_product_delivery_info(self):
        """Data passed to the checkout template for per-product carrier selection."""
        carriers = self._get_delivery_methods().sudo()
        result = []
        for line in self._get_shippable_lines():
            result.append({
                'line': line,
                'carriers': carriers,
                'selected_carrier': line.carrier_id,
            })
        return result

    def _rebuild_delivery_lines(self):
        """Rebuild grouped delivery lines after any per-product carrier change.

        Groups shippable lines by their chosen carrier_id. Each group gets ONE
        delivery line whose price is calculated on the combined weight of the group.
        Delivery lines for carriers no longer selected are removed.
        """
        self.ensure_one()
        # Force fresh read so cache from a previous iteration doesn't hide
        # lines just written by the controller.
        self.invalidate_recordset()

        # Remove ALL delivery lines (standard ones created by Odoo's default flow
        # have no source_line_ids and would otherwise survive and create duplicates)
        all_delivery_lines = self.env['sale.order.line'].search([
            ('order_id', '=', self.id),
            ('is_delivery', '=', True),
        ])
        all_delivery_lines.filtered(lambda l: l.qty_invoiced == 0).unlink()

        # Group shippable lines by selected carrier (re-read after unlink)
        self.invalidate_recordset()
        groups = {}
        for line in self._get_shippable_lines():
            if line.carrier_id:
                groups.setdefault(line.carrier_id, []).append(line)

        # Create one delivery line per carrier group
        for carrier, lines in groups.items():
            combined_weight = sum(
                (l.product_id.weight or 0.0) * l.product_uom_qty for l in lines
            )
            rate = carrier.sudo().with_context(
                order_weight=combined_weight
            ).rate_shipment(self)

            if not rate.get('success'):
                continue

            vals = self._prepare_delivery_line_vals(carrier, rate['price'])
            vals['source_line_ids'] = [(6, 0, [l.id for l in lines])]
            vals['carrier_id'] = carrier.id
            self.env['sale.order.line'].sudo().create(vals)

    def _check_carrier_quotation(self, force_carrier_id=None, keep_carrier=False):
        """Skip standard single-carrier logic for orders with shippable products.

        Odoo's default implementation creates ONE delivery line for the whole order.
        In per-product mode each physical product gets its own carrier selection, so
        we must never let the default logic run — it would create a duplicate/standard
        delivery line that survives alongside the per-product ones.
        """
        if self._has_shippable_products():
            # Remove any standard delivery line Odoo may have auto-created on a
            # previous call (no source_line_ids = created by the default flow)
            stale = self.env['sale.order.line'].search([
                ('order_id', '=', self.id),
                ('is_delivery', '=', True),
                ('source_line_ids', '=', False),
            ])
            stale.filtered(lambda l: l.qty_invoiced == 0).unlink()
            return True
        return super()._check_carrier_quotation(
            force_carrier_id=force_carrier_id, keep_carrier=keep_carrier
        )

    def _check_cart_is_ready_to_be_paid(self):
        """Per-product delivery validation: every physical product needs a carrier."""
        if self._has_shippable_products():
            if not self._is_cart_ready():
                raise ValidationError(_(
                    "Your cart is not ready to be paid, please verify previous steps."
                ))
            missing = self._get_shippable_lines().filtered(lambda l: not l.carrier_id)
            if missing:
                raise ValidationError(_(
                    "Please select a delivery method for all physical products."
                ))
            return
        return super()._check_cart_is_ready_to_be_paid()