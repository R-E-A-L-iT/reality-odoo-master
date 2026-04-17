from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class RentalOrderWizard(models.TransientModel):
    _inherit = "rental.order.wizard"

    def _remove_unselected_lines(self):
        for wizard in self:
            lines_to_remove = wizard.rental_wizard_line_ids.filtered(
                lambda l: l.order_line_id and l.order_line_id.selected != 'true'
            )
            if lines_to_remove:
                _logger.info(
                    "Rental pickup wizard %s: removing unselected lines %s",
                    wizard.id,
                    lines_to_remove.mapped("order_line_id").ids,
                )
                lines_to_remove.unlink()

    @api.model_create_multi
    def create(self, vals_list):
        wizards = super().create(vals_list)
        wizards._remove_unselected_lines()
        return wizards

    def write(self, vals):
        res = super().write(vals)
        self._remove_unselected_lines()
        return res

    def apply(self):
        self.rental_wizard_line_ids.filtered(
            lambda l: l.order_line_id and l.order_line_id.selected != 'true'
        ).unlink()
        return super().apply()