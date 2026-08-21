# -*- coding: utf-8 -*-

import logging
from odoo import fields, models

_logger = logging.getLogger(__name__)


class RentalOrderWizard(models.TransientModel):
    _inherit = "rental.order.wizard"

    def apply(self):
        target_by_order = self._get_target_status_by_order_before_apply()

        _logger.info("BEFORE super apply forced target map from order status: %s", target_by_order)

        res = super().apply()

        self._force_parent_kit_pickup_return_state(target_by_order)

        _logger.info(
            "AFTER super apply wizard.status=%s forced targets=%s",
            self.mapped("status"),
            target_by_order,
        )
        return res


    def _get_target_status_by_order_before_apply(self):
        target_by_order = {}

        for wizard in self:
            orders = wizard.rental_wizard_line_ids.mapped("order_line_id.order_id")

            for order in orders:
                current_status = order.rental_status

                _logger.info(
                    "Detecting rental wizard operation from ORDER status. order=%s current rental_status=%s wizard.status=%s context default_status=%s context status=%s",
                    order.name,
                    current_status,
                    wizard.status,
                    self.env.context.get("default_status"),
                    self.env.context.get("status"),
                )

                # Source of truth:
                # If the order is currently waiting for pickup, this wizard action is pickup.
                # If the order is currently waiting for return, this wizard action is return.
                if current_status == "pickup":
                    target_by_order[order.id] = "return"

                elif current_status == "return":
                    target_by_order[order.id] = "returned"

                else:
                    # Fallback only for unusual cases where order status is not useful.
                    operation = (
                        self.env.context.get("default_status")
                        or self.env.context.get("status")
                        or wizard.status
                    )

                    if operation == "pickup":
                        target_by_order[order.id] = "return"
                    elif operation == "return":
                        target_by_order[order.id] = "returned"

        return target_by_order

    def _force_order_rental_status_sql(self, order, target_status):
        # Critical:
        # Make Odoo finish all pending ORM writes/recomputes first.
        # Otherwise a later flush can overwrite our SQL update.
        self.env.flush_all()

        self.env.cr.execute("""
            UPDATE sale_order
            SET rental_status = %s,
                write_date = NOW(),
                write_uid = %s
            WHERE id = %s
        """, [target_status, self.env.uid, order.id])

        self.env.cr.execute("""
            SELECT rental_status
            FROM sale_order
            WHERE id = %s
        """, [order.id])

        _logger.info(
            "SQL check after FINAL force: order=%s rental_status=%s",
            order.name,
            self.env.cr.fetchone()[0],
        )

        order.invalidate_recordset(["rental_status"])

    def _force_parent_kit_pickup_return_state(self, target_by_order):
        SaleOrder = self.env["sale.order"].sudo()

        for wizard in self:
            component_sale_lines = wizard.rental_wizard_line_ids.mapped("order_line_id").filtered(
                lambda line: line.x_is_rental_kit_component and line.x_parent_rental_kit_line_id
            )

            parent_kit_lines = component_sale_lines.mapped("x_parent_rental_kit_line_id")

            for order_id, target_status in target_by_order.items():
                order = SaleOrder.browse(order_id)
                if not order.exists():
                    continue

                kit_lines_for_order = parent_kit_lines.filtered(
                    lambda line: line.order_id.id == order.id
                )

                if target_status == "return":
                    for kit_line in kit_lines_for_order:
                        kit_line.with_context(
                            bypass_sol_lock=True,
                            skip_apply_canadian_sales_taxes=True,
                            skip_company_consistency=True,
                        ).write({
                            "qty_delivered": kit_line.product_uom_qty,
                        })

                elif target_status == "returned":
                    for kit_line in kit_lines_for_order:
                        kit_line.with_context(
                            bypass_sol_lock=True,
                            skip_apply_canadian_sales_taxes=True,
                            skip_company_consistency=True,
                        ).write({
                            "qty_delivered": kit_line.product_uom_qty,
                            "qty_returned": kit_line.product_uom_qty,
                        })

                # This now flushes first, then forces SQL.
                self._force_order_rental_status_sql(order, target_status)

                _logger.info(
                    "FORCED rental order %s to rental_status=%s",
                    order.name,
                    target_status,
                )

class RentalOrderWizardLine(models.TransientModel):
    _inherit = "rental.order.wizard.line"

    allowed_lot_ids = fields.Many2many(
        "stock.lot",
        string="Allowed Serial Numbers",
    )