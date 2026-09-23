# -*- coding: utf-8 -*-
from odoo import api, models

LEAD_WATCHED = {
    "name", "type", "partner_id", "contact_name", "partner_name", "email_from",
    "phone", "mobile", "user_id", "team_id", "expected_revenue", "date_deadline",
    "priority", "tag_ids", "description", "company_id",
}


class CrmLead(models.Model):
    _inherit = "crm.lead"

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)
        self.env["upgrade.sync.event"]._enqueue("lead.upsert", leads)
        return leads

    def write(self, vals):
        # won/lost are captured by their own action methods; the stage change
        # they trigger must not be captured a second time.
        in_action = self.env.context.get("upgrade_sync_lead_action")
        res = super().write(vals)
        Event = self.env["upgrade.sync.event"]
        if LEAD_WATCHED.intersection(vals):
            Event._enqueue("lead.upsert", self)
        if "stage_id" in vals and not in_action:
            Event._enqueue("lead.stage", self)
        return res

    def action_set_won(self):
        res = super(CrmLead, self.with_context(upgrade_sync_lead_action=True)).action_set_won()
        self.env["upgrade.sync.event"]._enqueue("lead.won", self)
        return res

    def action_set_lost(self, **additional_values):
        res = super(CrmLead, self.with_context(upgrade_sync_lead_action=True)).action_set_lost(**additional_values)
        self.env["upgrade.sync.event"]._enqueue(
            "lead.lost", self,
            extra={"lost_reason_id": additional_values.get("lost_reason_id")},
        )
        return res
