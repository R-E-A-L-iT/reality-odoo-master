# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re

from datetime import datetime, timedelta
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api

_logger = logging.getLogger(__name__)

class StockLot(models.Model):
    _inherit = "stock.lot"

    owner = fields.Many2one("res.partner", string="Owner")

    document_pdf = fields.Binary(string="Attached PDF")
    document_pdf_filename = fields.Char(string="Filename")

    currency_id = fields.Many2one(related="company_id.currency_id")
    rental_order_ids = fields.Many2many(
        "sale.order", compute="_compute_rental_income", string="Rental Orders"
    )
    rental_order_count = fields.Integer(compute="_compute_rental_income")
    rental_income_total = fields.Monetary(
        compute="_compute_rental_income", currency_field="currency_id"
    )

    @api.depends("name")
    def _compute_rental_income(self):
        MoveLine = self.env["stock.move.line"].sudo()
        for lot in self:
            move_lines = MoveLine.search([
                ("lot_id", "=", lot.id),
                ("state", "=", "done"),
                ("picking_id.rental_sale_order_id", "!=", False),
            ])
            orders = move_lines.picking_id.rental_sale_order_id.filtered(
                lambda o: o.state != "cancel"
            )
            lot.rental_order_ids = orders
            lot.rental_order_count = len(orders)
            lot.rental_income_total = sum(orders.mapped("amount_total"))

    def action_view_rental_income(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Rental Income"),
            "res_model": "sale.order",
            "view_mode": "list,graph,form",
            "views": [
                (False, "list"),
                (self.env.ref("proquotes.view_order_graph_rental_income").id, "graph"),
                (False, "form"),
            ],
            "domain": [("id", "in", self.rental_order_ids.ids)],
            "context": {"create": False},
        }

    def copy_label(self):
        # Form Button Needs a Python Target Function
        return