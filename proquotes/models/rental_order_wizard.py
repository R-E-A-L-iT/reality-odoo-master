# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, Command

_logger = logging.getLogger(__name__)


class RentalOrderWizard(models.TransientModel):
    _inherit = "rental.order.wizard"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        ctx = dict(self.env.context or {})
        exploded_lines = ctx.get("x_exploded_pickup_lines") or []
        status = ctx.get("default_status")

        _logger.info("=== RENTAL WIZARD DEBUG START ===")
        _logger.info("RENTAL WIZARD DEBUG context: %s", ctx)
        _logger.info("RENTAL WIZARD DEBUG exploded_lines: %s", exploded_lines)
        _logger.info("RENTAL WIZARD DEBUG status: %s", status)
        _logger.info("RENTAL WIZARD DEBUG super default_get result: %s", res)

        if not exploded_lines:
            _logger.info("RENTAL WIZARD DEBUG no exploded lines found, keeping standard behavior")
            _logger.info("=== RENTAL WIZARD DEBUG END ===")
            return res

        line_commands = []

        for exploded in exploded_lines:
            product = self.env["product.product"].browse(exploded["product_id"])
            parent_line = self.env["sale.order.line"].browse(exploded["parent_sale_line_id"])
            qty = exploded.get("qty", 0.0) or 0.0

            if not product.exists():
                _logger.warning("RENTAL WIZARD DEBUG product not found for exploded line: %s", exploded)
                continue

            if not parent_line.exists():
                _logger.warning("RENTAL WIZARD DEBUG parent sale line not found for exploded line: %s", exploded)
                continue

            if qty <= 0:
                _logger.info("RENTAL WIZARD DEBUG skipping exploded line with qty <= 0: %s", exploded)
                continue

            allowed_lot_ids = exploded.get("allowed_lot_ids") or []

            pickeable_lot_ids = self._get_pickeable_serial_lot_ids_for_product(
                product,
                parent_line.company_id,
            )

            vals = {
                "status": status,
                "order_line_id": parent_line.id,
                "product_id": product.id,
                "qty_reserved": qty,
            }

            if product.tracking == "serial":
                vals["tracking"] = "serial"
                vals["pickeable_lot_ids"] = [Command.set(pickeable_lot_ids)]
                vals["qty_available"] = len(pickeable_lot_ids)
            else:
                vals["qty_available"] = qty

            if allowed_lot_ids:
                vals["allowed_lot_ids"] = [Command.set(allowed_lot_ids)]

            if status == "pickup":
                vals["qty_delivered"] = qty
            elif status == "return":
                vals["qty_returned"] = qty

            line_commands.append(Command.create(vals))
            _logger.info("RENTAL WIZARD DEBUG appended wizard line vals: %s", vals)

        _logger.info("RENTAL WIZARD DEBUG final line_commands: %s", line_commands)

        res["rental_wizard_line_ids"] = line_commands

        _logger.info("RENTAL WIZARD DEBUG final default_get result: %s", res)
        _logger.info("=== RENTAL WIZARD DEBUG END ===")

        return res

    def _get_pickeable_serial_lot_ids_for_product(self, product, company):
        if product.tracking != "serial":
            return []

        quants = self.env["stock.quant"].sudo().search([
            ("product_id", "=", product.id),
            ("lot_id", "!=", False),
            ("location_id.usage", "=", "internal"),
            "|",
                ("company_id", "=", False),
                ("company_id", "=", company.id),
        ])

        lot_ids = []

        for quant in quants:
            available_qty = quant.quantity - quant.reserved_quantity
            if available_qty > 0:
                lot_ids.append(quant.lot_id.id)

        return list(set(lot_ids))

class RentalOrderWizardLine(models.TransientModel):
    _inherit = "rental.order.wizard.line"

    allowed_lot_ids = fields.Many2many(
        "stock.lot",
        string="Allowed Serial Numbers",
    )