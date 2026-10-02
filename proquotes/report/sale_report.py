# -*- coding: utf-8 -*-

from odoo import models


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _where_sale(self):
        """Keep the core filters and only include lines with selected = 'true'."""
        base_where = super()._where_sale()
        return f"""
            {base_where}
            AND l.selected = 'true'"""