from odoo import models
from odoo.tools import SQL


class RentalSchedule(models.Model):
    _inherit = "sale.rental.schedule"

    def _query(self) -> SQL:
        return SQL("""
            %s (SELECT %s
                FROM %s
                WHERE sol.product_id IS NOT NULL
                    AND sol.is_rental
                    AND sol.is_selected
                    AND t.type != 'combo'
                GROUP BY %s)
            """,
            self._with(),
            self._select(),
            self._from(),
            self._groupby()
        )
