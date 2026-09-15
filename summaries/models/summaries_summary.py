import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

DEFAULT_WEEKS = 12
MAX_WEEKS = 52


class SummariesSummary(models.Model):
    _name = "summaries.summary"
    _description = "Daily Summary"
    _order = "date desc, user_id"

    name = fields.Char(compute="_compute_name", store=True)
    user_id = fields.Many2one(
        "res.users", string="User", required=True, index=True, ondelete="cascade",
        default=lambda self: self.env.user,
    )
    date = fields.Date(required=True, index=True, default=fields.Date.context_today)
    company_id = fields.Many2one(
        "res.company", default=lambda self: self.env.company, index=True
    )

    body = fields.Html(
        string="Notes", sanitize_attributes=False,
        help="Free-form notes: checklists written as text, images, tables, links.",
    )
    objective_ids = fields.One2many("summaries.objective", "summary_id", string="Objectives")

    objective_count = fields.Integer(compute="_compute_progress", store=True)
    objective_done_count = fields.Integer(compute="_compute_progress", store=True)
    progress = fields.Float(
        string="Progress", compute="_compute_progress", store=True, group_operator="avg",
        help="Share of the day's objectives that are done.",
    )

    is_summaries_manager = fields.Boolean(compute="_compute_is_summaries_manager")

    _sql_constraints = [
        ("summaries_summary_unique_day", "unique(user_id, date)",
         "A user can only have one summary per day."),
    ]

    @api.depends("user_id", "date")
    def _compute_name(self):
        for summary in self:
            day = fields.Date.to_string(summary.date) or ""
            summary.name = "%s — %s" % (summary.user_id.name or "", day)

    @api.depends("objective_ids", "objective_ids.done")
    def _compute_progress(self):
        for summary in self:
            objectives = summary.objective_ids
            done = objectives.filtered("done")
            summary.objective_count = len(objectives)
            summary.objective_done_count = len(done)
            summary.progress = (100.0 * len(done) / len(objectives)) if objectives else 0.0

    def _compute_is_summaries_manager(self):
        is_manager = self.env.user.has_group("summaries.group_summaries_manager")
        for summary in self:
            summary.is_summaries_manager = is_manager

    # ------------------------------------------------------------------
    # actions
    # ------------------------------------------------------------------

    @api.model
    def action_open_today(self):
        """Open (creating it if needed) today's summary of the current user."""
        summary = self._get_or_create(self.env.user, fields.Date.context_today(self))
        return {
            "type": "ir.actions.act_window",
            "name": _("Today's Summary"),
            "res_model": self._name,
            "res_id": summary.id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    @api.model
    def _get_or_create(self, user, day):
        summary = self.search(
            [("user_id", "=", user.id), ("date", "=", day)], limit=1
        )
        if not summary:
            summary = self.create({"user_id": user.id, "date": day})
        return summary

    def action_mark_all_done(self):
        self.ensure_one()
        self.objective_ids.filtered(lambda o: not o.done).write({"done": True})
        return True

    # ------------------------------------------------------------------
    # daily creation
    # ------------------------------------------------------------------

    @api.model
    def _summary_users(self):
        """Active internal users that should get a summary."""
        return self.env["res.users"].search([("share", "=", False), ("active", "=", True)])

    @api.model
    def _cron_create_daily_summaries(self):
        """Create an empty summary for every internal user, on business days."""
        today = fields.Date.context_today(self)
        if today.weekday() >= 5:  # Saturday, Sunday
            return False
        users = self._summary_users()
        existing = self.search([("date", "=", today), ("user_id", "in", users.ids)])
        missing = users - existing.mapped("user_id")
        for user in missing:
            self.create({"user_id": user.id, "date": today})
        _logger.info("Summaries: created %s summaries for %s", len(missing), today)
        return True

    # ------------------------------------------------------------------
    # API for AI users
    # ------------------------------------------------------------------

    @api.model
    def upsert_summary(self, user_ref, day=None, body=None, objectives=None, replace_objectives=True):
        """Create or update one user's summary for a day.

        :param user_ref: user id, or login
        :param day: date string, defaults to today
        :param body: HTML notes, replaces the current notes when given
        :param objectives: list of dicts with keys name, note, done, record_ref
            ("model,id" string), sequence
        :param replace_objectives: drop the existing objectives first
        :return: the summary id
        """
        user = self._resolve_user(user_ref)
        day = fields.Date.to_date(day) if day else fields.Date.context_today(self)
        summary = self._get_or_create(user, day)

        if body is not None:
            summary.body = body

        if objectives is not None:
            if replace_objectives:
                summary.objective_ids.unlink()
            sequence = 10
            for objective in objectives:
                values = {
                    "summary_id": summary.id,
                    "name": objective.get("name"),
                    "note": objective.get("note"),
                    "done": bool(objective.get("done")),
                    "sequence": objective.get("sequence", sequence),
                    "record_ref": objective.get("record_ref") or False,
                }
                if not values["name"]:
                    raise UserError(_("Every objective needs a name."))
                self.env["summaries.objective"].create(values)
                sequence += 10
        return summary.id

    @api.model
    def _resolve_user(self, user_ref):
        Users = self.env["res.users"]
        if isinstance(user_ref, int):
            user = Users.browse(user_ref).exists()
        else:
            user = Users.search([("login", "=", user_ref)], limit=1)
        if not user:
            raise UserError(_("No user found for %s.", user_ref))
        return user

    # ------------------------------------------------------------------
    # performance stats
    # ------------------------------------------------------------------

    def _stats_buckets(self, weeks):
        """Weekly (Monday to Monday) buckets ending with the current week."""
        today = fields.Date.context_today(self)
        this_monday = today - timedelta(days=today.weekday())
        first = this_monday - timedelta(weeks=weeks - 1)
        return [
            (first + timedelta(weeks=index), first + timedelta(weeks=index + 1))
            for index in range(weeks)
        ]

    @api.model
    def _user_has_group(self, user, xmlid):
        group = self.env.ref(xmlid, raise_if_not_found=False)
        return bool(group) and group in user.sudo().groups_id

    def _stats_series(self, model, domain, date_field, buckets, measure=None):
        """Weekly totals for a model, as one value per bucket."""
        empty = [0.0] * len(buckets)
        if model not in self.env:
            return empty
        aggregates = ["%s:sum" % measure] if measure else []
        try:
            groups = self.env[model].sudo().read_group(
                domain, aggregates, ["%s:week" % date_field], lazy=False
            )
        except Exception:
            # a model can differ between versions; a missing stat beats a crash
            _logger.exception("Summaries: could not read %s stats", model)
            return empty
        values = {start: 0.0 for start, _end in buckets}
        for group in groups:
            date_range = (group.get("__range") or {}).get("%s:week" % date_field) or {}
            start = date_range.get("from")
            if not start:
                continue
            start = fields.Date.to_date(start)
            if start in values:
                values[start] = group.get(measure) if measure else group.get("__count") or 0
        return [round(values[start] or 0.0, 2) for start, _end in buckets]

    def _stats_sales(self, user, buckets):
        if "sale.order" not in self.env:
            return []
        start = fields.Date.to_string(buckets[0][0])
        sent = [("user_id", "=", user.id), ("date_order", ">=", start),
                ("state", "in", ["sent", "sale", "done"])]
        won = [("user_id", "=", user.id), ("date_order", ">=", start),
               ("state", "in", ["sale", "done"])]
        return [
            {
                "key": "sales_quotes",
                "title": _("Quotes sent vs confirmed"),
                "type": "bar",
                "datasets": [
                    {"label": _("Sent"), "data": self._stats_series("sale.order", sent, "date_order", buckets)},
                    {"label": _("Confirmed"), "data": self._stats_series("sale.order", won, "date_order", buckets)},
                ],
                "drilldown": {"model": "sale.order", "date_field": "date_order", "domain": sent},
            },
            {
                "key": "sales_revenue",
                "title": _("Revenue confirmed (untaxed)"),
                "type": "line",
                "datasets": [
                    {"label": _("Revenue"), "data": self._stats_series(
                        "sale.order", won, "date_order", buckets, measure="amount_untaxed")},
                ],
                "drilldown": {"model": "sale.order", "date_field": "date_order", "domain": won},
            },
        ]

    def _stats_crm(self, user, buckets):
        if "crm.lead" not in self.env:
            return []
        start = fields.Date.to_string(buckets[0][0])
        created = [("user_id", "=", user.id), ("create_date", ">=", start)]
        won = [("user_id", "=", user.id), ("date_closed", ">=", start), ("stage_id.is_won", "=", True)]
        return [
            {
                "key": "crm_pipeline",
                "title": _("Leads created vs won"),
                "type": "bar",
                "datasets": [
                    {"label": _("Created"), "data": self._stats_series("crm.lead", created, "create_date", buckets)},
                    {"label": _("Won"), "data": self._stats_series("crm.lead", won, "date_closed", buckets)},
                ],
                "drilldown": {"model": "crm.lead", "date_field": "create_date", "domain": created},
            },
            {
                "key": "crm_revenue",
                "title": _("Expected revenue won"),
                "type": "line",
                "datasets": [
                    {"label": _("Expected revenue"), "data": self._stats_series(
                        "crm.lead", won, "date_closed", buckets, measure="expected_revenue")},
                ],
                "drilldown": {"model": "crm.lead", "date_field": "date_closed", "domain": won},
            },
        ]

    def _stats_projects(self, user, buckets):
        Task = self.env.get("project.task")
        if Task is None or "state" not in Task._fields:
            return []
        start = fields.Date.to_string(buckets[0][0])
        done = [("user_ids", "in", user.id), ("state", "=", "1_done"),
                ("date_last_stage_update", ">=", start)]
        return [{
            "key": "tasks_done",
            "title": _("Tasks completed"),
            "type": "bar",
            "datasets": [
                {"label": _("Tasks"), "data": self._stats_series(
                    "project.task", done, "date_last_stage_update", buckets)},
            ],
            "drilldown": {"model": "project.task", "date_field": "date_last_stage_update", "domain": done},
        }]

    def _stats_timesheets(self, user, buckets):
        Line = self.env.get("account.analytic.line")
        if Line is None or "project_id" not in Line._fields:
            return []
        start = fields.Date.to_string(buckets[0][0])
        logged = [("user_id", "=", user.id), ("date", ">=", start), ("project_id", "!=", False)]
        return [{
            "key": "timesheet_hours",
            "title": _("Hours logged"),
            "type": "line",
            "datasets": [
                {"label": _("Hours"), "data": self._stats_series(
                    "account.analytic.line", logged, "date", buckets, measure="unit_amount")},
            ],
            "drilldown": {"model": "account.analytic.line", "date_field": "date", "domain": logged},
        }]

    def get_performance_stats(self, weeks=DEFAULT_WEEKS):
        """Charts for this summary's user, picked from the groups they are in."""
        self.ensure_one()
        try:
            weeks = int(weeks or DEFAULT_WEEKS)
        except (TypeError, ValueError):
            weeks = DEFAULT_WEEKS
        weeks = max(2, min(weeks, MAX_WEEKS))

        user = self.user_id
        buckets = self._stats_buckets(weeks)
        charts = []
        if self._user_has_group(user, "sales_team.group_sale_salesman"):
            charts += self._stats_sales(user, buckets)
            charts += self._stats_crm(user, buckets)
        if self._user_has_group(user, "project.group_project_user"):
            charts += self._stats_projects(user, buckets)
        if self._user_has_group(user, "hr_timesheet.group_hr_timesheet_user"):
            charts += self._stats_timesheets(user, buckets)

        return {
            "user_name": user.name,
            "weeks": weeks,
            "labels": [start.strftime("%b %d") for start, _end in buckets],
            "ranges": [
                [fields.Date.to_string(start), fields.Date.to_string(end)]
                for start, end in buckets
            ],
            "charts": charts,
        }
