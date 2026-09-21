from odoo import _, api, fields, models
from odoo.exceptions import UserError

# documents an objective can point at, when the module is installed
LINKABLE_MODELS = [
    "sale.order",
    "crm.lead",
    "account.move",
    "project.task",
    "purchase.order",
    "stock.picking",
    "helpdesk.ticket",
    "res.partner",
]


class SummariesObjective(models.Model):
    _name = "summaries.objective"
    _description = "Daily Summary Objective"
    _order = "summary_id, sequence, id"

    summary_id = fields.Many2one(
        "summaries.summary", string="Summary", required=True, ondelete="cascade", index=True
    )
    user_id = fields.Many2one(related="summary_id.user_id", store=True, index=True)
    date = fields.Date(related="summary_id.date", store=True, index=True)
    sequence = fields.Integer(default=10)

    name = fields.Char(string="Objective", required=True)
    note = fields.Char(string="Detail")
    done = fields.Boolean(string="Done")
    done_date = fields.Datetime(string="Completed On", readonly=True)

    record_ref = fields.Reference(
        selection="_selection_target_model",
        string="Related Document",
        help="The quote, opportunity, task or other document this objective is about.",
    )
    execute_enabled = fields.Boolean(
        string="Can Be Executed",
        help="Shows an Execute button on the task, for an AI to carry it out. "
             "The webhook behind it is not wired up yet.",
    )

    @api.model
    def _selection_target_model(self):
        return [
            (model, self.env[model]._description or model)
            for model in LINKABLE_MODELS
            if model in self.env
        ]

    def write(self, vals):
        if "done" in vals:
            vals = dict(vals, done_date=fields.Datetime.now() if vals["done"] else False)
        return super().write(vals)

    def action_open_record(self):
        """Open the linked document."""
        self.ensure_one()
        if not self.record_ref:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.record_ref._name,
            "res_id": self.record_ref.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    def _task_data(self):
        """Values the document view renders for one task."""
        self.ensure_one()
        reference = False
        if self.record_ref:
            try:
                reference = {
                    "model": self.record_ref._name,
                    "id": self.record_ref.id,
                    "display_name": self.record_ref.sudo().display_name,
                }
            except Exception:
                reference = False
        return {
            "id": self.id,
            "name": self.name,
            "note": self.note or "",
            "done": self.done,
            "sequence": self.sequence,
            "execute_enabled": self.execute_enabled,
            "ref": reference,
        }

    def action_execute(self):
        """Placeholder for handing the task to an AI over a webhook."""
        self.ensure_one()
        raise UserError(_(
            "Executing a task automatically is not set up yet."
        ))
