from odoo import models


class RentalSchedule(models.Model):
    _inherit = "sale.rental.schedule"

    def _query(self):
        """Core sale_renting keeps ``product_id`` and ``is_rental``.

        ``selected`` is the source of truth. It is required and defaults to
        ``'true'``, so a rental line the ORM creates without the key (the
        rental wizard, or a pickup/return extra line) is stored as ``'true'``
        and stays on the schedule. NULL or '' is not written by that path;
        if a row still has one, it means the same as the default and stays
        included. Explicit ``'false'`` is excluded. ``is_selected`` is only
        the form checkbox and is often stale on existing rows.
        """
        return """
            %s (SELECT %s
                FROM %s
                WHERE sol.product_id IS NOT NULL
                    AND sol.is_rental
                    AND COALESCE(NULLIF(sol.selected, ''), 'true') = 'true'
                GROUP BY %s)
        """ % (
            self._with(),
            self._select(),
            self._from(),
            self._groupby()
        )
