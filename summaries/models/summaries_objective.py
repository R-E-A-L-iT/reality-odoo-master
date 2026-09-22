import json
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

ACTORS = ("ai", "human")

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
    plan = fields.Text(
        string="Plan",
        help="JSON plan of steps written by an AI: "
             '{"steps": [{"text": "...", "actor": "ai"|"human"}]}',
    )
    has_plan = fields.Boolean(compute="_compute_has_plan")
    plan_executed_on = fields.Datetime(string="Plan Sent For Execution", readonly=True)

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

    @api.depends("plan")
    def _compute_has_plan(self):
        for objective in self:
            objective.has_plan = bool(objective._plan_steps())

    def _plan_steps(self):
        """The plan's steps, or an empty list when there is no usable plan."""
        self.ensure_one()
        try:
            plan = json.loads(self.plan or "{}")
        except (TypeError, ValueError):
            _logger.warning("Summaries: task %s holds invalid JSON in plan", self.id)
            return []
        steps = plan.get("steps") if isinstance(plan, dict) else plan
        return steps if isinstance(steps, list) else []

    @api.model
    def _clean_plan(self, plan):
        """Validate a plan coming from an AI or from the editor."""
        if isinstance(plan, str):
            try:
                plan = json.loads(plan or "{}")
            except ValueError as error:
                raise UserError(_("The plan is not valid JSON: %s", error))
        steps = plan.get("steps") if isinstance(plan, dict) else plan
        if steps is None:
            steps = []
        if not isinstance(steps, (list, tuple)):
            raise UserError(_("A plan must hold a list of steps."))

        cleaned = []
        for step in steps:
            if isinstance(step, str):
                step = {"text": step}
            if not isinstance(step, dict):
                raise UserError(_("Every step must be an object or a string."))
            text = (step.get("text") or "").strip()
            if not text:
                raise UserError(_("Every step needs some text."))
            actor = (step.get("actor") or "human").strip().lower()
            if actor not in ACTORS:
                raise UserError(_(
                    "Unknown step actor %(actor)s. Use one of: %(allowed)s",
                    actor=actor, allowed=", ".join(ACTORS),
                ))
            cleaned.append({
                "text": text,
                "actor": actor,
                "note": (step.get("note") or "").strip(),
                "done": bool(step.get("done")),
            })
        result = {"steps": cleaned}
        if isinstance(plan, dict) and plan.get("summary"):
            result["summary"] = str(plan["summary"])
        return result

    def set_plan(self, plan):
        """Replace the plan. Accepts the editor's object or an AI's JSON."""
        self.ensure_one()
        cleaned = self._clean_plan(plan)
        self.plan = json.dumps(cleaned, ensure_ascii=False, indent=2) if cleaned["steps"] else False
        return self.get_plan()

    def get_plan(self):
        self.ensure_one()
        try:
            stored = json.loads(self.plan or "{}")
        except (TypeError, ValueError):
            stored = {}
        return {
            "task_id": self.id,
            "task_name": self.name,
            "summary": (stored or {}).get("summary", "") if isinstance(stored, dict) else "",
            "steps": self._plan_steps(),
            "executed_on": fields.Datetime.to_string(self.plan_executed_on),
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
            "has_plan": self.has_plan,
            "plan_executed_on": fields.Datetime.to_string(self.plan_executed_on),
            "ref": reference,
        }

    def _execute_subuser(self):
        """Who carries the plan out: the reader's default AI assistant."""
        self.ensure_one()
        if "promessaging.subuser" not in self.env:
            return self.env["promessaging.subuser"] if "promessaging.subuser" in self.env else None
        return self.env.user._promessaging_default_subuser()

    def action_execute(self):
        """Hand the task, and its plan, to an AI to carry out."""
        self.ensure_one()
        subuser = self._execute_subuser()
        if not subuser:
            raise UserError(_(
                "No AI assistant to execute this. Set a Default AI Assistant on your "
                "user, under Settings, Users, Access Rights."
            ))

        reference = False
        if self.record_ref:
            try:
                reference = {
                    "model": self.record_ref._name,
                    "id": self.record_ref.id,
                    "name": self.record_ref.sudo().display_name,
                }
            except Exception:
                reference = False

        payload = {
            "prompt": _("Carry out this task, following the plan's AI steps."),
            "task": {
                "id": self.id,
                "name": self.name,
                "note": self.note or "",
                "done": self.done,
                "document": reference,
            },
            "summary": {
                "id": self.summary_id.id,
                "date": fields.Date.to_string(self.summary_id.date),
                "user": {
                    "id": self.summary_id.user_id.id,
                    "name": self.summary_id.user_id.name,
                },
            },
            "plan": self.get_plan(),
            "requested_by": {"user_id": self.env.user.id, "name": self.env.user.name},
            "reply": subuser.sudo()._reply_instructions(),
        }
        # answers about this task come back to the task itself
        payload["reply"]["async"]["body"]["objective_id"] = self.id
        payload["reply"]["sync"] = _(
            'Answer with JSON {"plan": {"steps": [...]}} to update the plan, or '
            '{"reply": "text"} to report back.'
        )

        result = subuser.sudo().dispatch("task_execute", payload)
        if result.get("ok"):
            self.plan_executed_on = fields.Datetime.now()
            reply = (result.get("data") or {}).get("plan")
            if reply:
                self.set_plan(reply)
        return {
            "ok": bool(result.get("ok")),
            "error": result.get("error"),
            "subuser": subuser.sudo().name,
        }

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
