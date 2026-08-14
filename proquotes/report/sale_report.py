# -*- coding: utf-8 -*-

from odoo import models


class SaleReport(models.Model):
    _inherit = "sale.report"

    def _where_sale(self):
        """Override to exclude hidden rental-kit component lines from the report."""
        base_where = super()._where_sale()
        return f"""
            {base_where}
            AND COALESCE(l.x_is_rental_kit_component, FALSE) = FALSE"""