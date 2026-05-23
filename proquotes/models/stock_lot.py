# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo import models, fields


class StockLot(models.Model):
    _inherit = "stock.lot"

    owner = fields.Many2one("res.partner", string="Owner")

    document_pdf = fields.Binary(string="Attached PDF")
    document_pdf_filename = fields.Char(string="Filename")

    def copy_label(self):
        # Form Button Needs a Python Target Function
        return
