# -*- coding: utf-8 -*-

import logging
from odoo import api, models, Command

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

            vals = {
                "status": status,
                "order_line_id": parent_line.id,
                "product_id": product.id,
                "qty_reserved": qty,
            }

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