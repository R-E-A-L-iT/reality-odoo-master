import json
import logging
from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_sanitize

_logger = logging.getLogger(__name__)

DEFAULT_WEEKS = 12
DEFAULT_CONTENT = [
    {"type": "section", "title": "Main objectives", "style": "primary", "blocks": [
        {"type": "text", "text": "*No objectives written yet.*"},
    ]},
    {"type": "section", "title": "Looking ahead", "style": "info", "blocks": [
        {"type": "text", "text": "*No insights yet.*"},
    ]},
    {"type": "stats"},
]

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

    intro = fields.Text(
        string="Intro",
        default="[]",
        help="JSON list of content blocks rendered above the tasks. Free-form: "
             "whatever the day needs (briefing, meeting notes, warnings).",
    )
    content = fields.Text(
        string="Content",
        default=lambda self: json.dumps(DEFAULT_CONTENT, indent=2),
        help="JSON list of content blocks rendered below the tasks. "
             "Call get_content_schema() for the accepted block types.",
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
    def upsert_summary(self, user_ref, day=None, content=None, objectives=None,
                       replace_objectives=True, intro=None):
        """Create or update one user's summary for a day.

        :param user_ref: user id, or login
        :param day: date string, defaults to today
        :param content: list of content blocks below the tasks, replaces the
            current content when given (see get_content_schema())
        :param intro: list of content blocks above the tasks, free-form
        :param objectives: list of dicts with keys name, note, done, record_ref
            ("model,id" string), sequence, and plan ({"steps": [...]})
        :param replace_objectives: drop the existing objectives first
        :return: the summary id
        """
        user = self._resolve_user(user_ref)
        day = fields.Date.to_date(day) if day else fields.Date.context_today(self)
        summary = self._get_or_create(user, day)

        if intro is not None:
            summary.set_intro(intro)

        if content is not None:
            summary.set_content(content)

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
                task = self.env["summaries.objective"].create(values)
                if objective.get("plan"):
                    task.set_plan(objective["plan"])
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
    # document content
    # ------------------------------------------------------------------

    BLOCK_TYPES = (
        "heading", "text", "callout", "list", "checklist", "kpi", "progress",
        "table", "links", "image", "divider", "html", "section", "stats",
    )
    BLOCK_STYLES = ("default", "primary", "success", "warning", "danger", "info", "muted")

    def _parse_blocks(self, field_name="content"):
        self.ensure_one()
        try:
            blocks = json.loads(self[field_name] or "[]")
        except (TypeError, ValueError):
            _logger.warning("Summaries: summary %s holds invalid JSON in %s", self.id, field_name)
            return []
        return blocks if isinstance(blocks, list) else []

    @api.model
    def _clean_blocks(self, blocks, depth=0):
        """Validate blocks, drop unknown keys, sanitize raw html."""
        if depth > 3:
            raise UserError(_("Content blocks are nested too deeply."))
        if not isinstance(blocks, (list, tuple)):
            raise UserError(_("Content must be a list of blocks."))

        cleaned = []
        for block in blocks:
            if not isinstance(block, dict):
                raise UserError(_("Every content block must be an object."))
            block_type = block.get("type")
            if block_type not in self.BLOCK_TYPES:
                raise UserError(_(
                    "Unknown content block type %(type)s. Allowed types: %(allowed)s",
                    type=block_type, allowed=", ".join(self.BLOCK_TYPES),
                ))
            clean = dict(block)
            style = clean.get("style")
            if block_type in ("callout", "kpi", "progress", "heading") and style and style not in self.BLOCK_STYLES:
                raise UserError(_(
                    "Unknown style %(style)s. Allowed styles: %(allowed)s",
                    style=style, allowed=", ".join(self.BLOCK_STYLES),
                ))
            if block_type == "html":
                clean["html"] = html_sanitize(clean.get("html") or "")
            if block_type == "section":
                clean["blocks"] = self._clean_blocks(clean.get("blocks") or [], depth + 1)
            cleaned.append(clean)
        return cleaned

    def _set_blocks(self, blocks, field_name="content"):
        self.ensure_one()
        if isinstance(blocks, str):
            try:
                blocks = json.loads(blocks or "[]")
            except ValueError as error:
                raise UserError(_("%(field)s is not valid JSON: %(error)s",
                                  field=field_name.capitalize(), error=error))
        self[field_name] = json.dumps(self._clean_blocks(blocks), ensure_ascii=False, indent=2)
        return True

    def set_content(self, blocks):
        """Replace the blocks shown below the tasks. List or JSON string."""
        return self._set_blocks(blocks, "content")

    def set_intro(self, blocks):
        """Replace the free-form blocks shown above the tasks. List or JSON string."""
        return self._set_blocks(blocks, "intro")

    def get_document(self):
        """Everything the document view renders, in one call."""
        self.ensure_one()
        return {
            "id": self.id,
            "name": self.name,
            "progress": self.progress,
            "task_count": self.objective_count,
            "task_done_count": self.objective_done_count,
            "tasks": [task._task_data() for task in self.objective_ids],
            "intro_blocks": self._parse_blocks("intro"),
            "intro": self.intro or "[]",
            "blocks": self._parse_blocks("content"),
            "content": self.content or "[]",
        }

    @api.model
    def get_content_schema(self):
        """Block reference, for the bots writing these summaries."""
        return {
            "fields": {
                "intro": "Blocks rendered above the tasks. Free-form: briefing, "
                         "meeting notes, anything the day needs.",
                "content": "Blocks rendered below the tasks: objectives, insights, stats.",
            },
            "styles": list(self.BLOCK_STYLES),
            "inline_markup": {
                "bold": "**bold**",
                "italic": "*italic*",
                "code": "`code`",
                "link": "[label](https://example.com)",
                "document": "[label](odoo:sale.order:42) opens that record in Odoo",
            },
            "blocks": [
                {"type": "heading", "text": "Main objectives", "level": 2, "style": "primary"},
                {"type": "text", "text": "Any **inline** markup, [a quote](odoo:sale.order:42)."},
                {"type": "callout", "style": "warning", "title": "Watch out",
                 "text": "Renewal expires Friday."},
                {"type": "list", "style": "bullet", "items": ["First", "Second"]},
                {"type": "checklist", "items": [{"text": "Reviewed", "done": True}]},
                {"type": "kpi", "items": [
                    {"label": "Quotes sent", "value": "12", "delta": "+3", "style": "success"}]},
                {"type": "progress", "label": "Pipeline target", "value": 65, "style": "success"},
                {"type": "table", "columns": ["Quote", "Value"], "rows": [["QT-1", "$1,200"]]},
                {"type": "links", "items": [
                    {"label": "QT-123456", "model": "sale.order", "id": 42},
                    {"label": "Docs", "url": "https://example.com"}]},
                {"type": "image", "src": "/web/image/...", "alt": "Chart", "width": "100%"},
                {"type": "divider"},
                {"type": "html", "html": "<b>sanitized</b> raw html"},
                {"type": "section", "title": "Tomorrow", "style": "info", "blocks": [
                    {"type": "text", "text": "Nested blocks go here."}]},
                {"type": "stats", "note": "Renders this user's role-based performance graphs."},
            ],
        }

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
