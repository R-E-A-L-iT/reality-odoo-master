from odoo import api, models

class RentalOrderWizard(models.TransientModel):
    _inherit = "rental.order.wizard"   # replace with exact model name

    def apply(self):
        for wizard in self:
            wizard.rental_wizard_line_ids = wizard.rental_wizard_line_ids.filtered(
                lambda l: l.order_line_id.selected == 'true'
            )
        return super().apply()

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)

        if vals.get("rental_wizard_line_ids"):
            filtered_commands = []
            order_line_ids_to_keep = set()

            for command in vals["rental_wizard_line_ids"]:
                # usually (0, 0, values)
                if isinstance(command, (list, tuple)) and len(command) >= 3 and command[0] == 0:
                    line_vals = command[2]
                    order_line_id = line_vals.get("order_line_id")
                    if order_line_id:
                        order_line_ids_to_keep.add(order_line_id)

            selected_ids = set(
                self.env["sale.order.line"].browse(list(order_line_ids_to_keep)).filtered(
                    lambda l: l.selected == 'true'
                ).ids
            )

            for command in vals["rental_wizard_line_ids"]:
                if isinstance(command, (list, tuple)) and len(command) >= 3 and command[0] == 0:
                    line_vals = command[2]
                    if line_vals.get("order_line_id") in selected_ids:
                        filtered_commands.append(command)
                else:
                    filtered_commands.append(command)

            vals["rental_wizard_line_ids"] = filtered_commands

        return vals