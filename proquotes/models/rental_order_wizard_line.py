# -*- coding: utf-8 -*-

from odoo import fields, models


class RentalOrderWizardLine(models.TransientModel):
    _inherit = "rental.order.wizard.line"

    allowed_lot_ids = fields.Many2many(
        "stock.lot",
        string="Allowed Serial Numbers",
    )
