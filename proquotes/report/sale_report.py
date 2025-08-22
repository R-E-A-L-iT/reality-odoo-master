# -*- coding: utf-8 -*-

from odoo import models


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _where_sale(self):
        """Override to filter only selected sale order lines where is_selected = True"""
        base_where = super()._where_sale()
        return f"""
            {base_where}
            AND l.is_selected = true"""