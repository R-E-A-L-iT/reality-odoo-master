# -*- coding: utf-8 -*-
from odoo import fields, models

class StockLot(models.Model):
    _inherit = "stock.lot"

    envio_package_id = fields.Many2one(
        "envio.package",
        string="Envio Device",
        ondelete="set null",
        index=True,
    )
