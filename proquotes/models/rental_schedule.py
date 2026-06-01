from odoo import models


class RentalSchedule(models.Model):
    _inherit = "sale.rental.schedule"

    def _query(self):
        return """
            %s (SELECT %s
                FROM %s
                WHERE sol.product_id IS NOT NULL
                    AND sol.is_rental
                    AND sol.is_selected
                GROUP BY %s)
        """ % (
            self._with(),
            self._select(),
            self._from(),
            self._groupby()
        )
