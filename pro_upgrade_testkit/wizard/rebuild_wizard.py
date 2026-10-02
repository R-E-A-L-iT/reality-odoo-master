# -*- coding: utf-8 -*-

from odoo import fields, models, _


class ProUpgradeTestkitWizard(models.TransientModel):
    _name = "pro.upgrade.testkit.wizard"
    _description = "Rebuild Enginelly Test Suite"

    last_run_id = fields.Many2one(
        "pro.upgrade.test.run",
        string="Last run",
        readonly=True,
    )
    report_html = fields.Html(
        related="last_run_id.report_html",
        readonly=True,
        string="Run report",
    )
    state = fields.Selection(related="last_run_id.state", readonly=True)

    def action_rebuild(self):
        self.ensure_one()
        run = self.env["pro.upgrade.test.run"]._rebuild_suite()
        self.last_run_id = run.id
        return {
            "type": "ir.actions.act_window",
            "name": _("Rebuild Enginelly test suite"),
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    def action_open_run(self):
        self.ensure_one()
        if not self.last_run_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "name": _("Enginelly test run"),
            "res_model": "pro.upgrade.test.run",
            "res_id": self.last_run_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def action_open_orders(self):
        self.ensure_one()
        if not self.last_run_id:
            return False
        return self.last_run_id.action_view_orders()
