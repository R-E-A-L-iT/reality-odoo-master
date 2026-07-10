from odoo import api, fields, models


class Lead2OpportunityPartner(models.TransientModel):
    """Adds a Company picker to the single "Convert to Opportunity" wizard so
    the user can confirm/swap which company the resulting opportunity lands in.
    Defaults to the lead's current company."""
    _inherit = "crm.lead2opportunity.partner"

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        default=lambda self: self._default_convert_company(),
        help="The company the opportunity will be created in. Defaults to the "
             "lead's current company; change it here if it should differ.",
    )

    @api.model
    def _default_convert_company(self):
        lead_ids = self.env.context.get("active_ids") or (
            [self.env.context["active_id"]] if self.env.context.get("active_id") else []
        )
        if lead_ids:
            lead = self.env["crm.lead"].browse(lead_ids[0])
            if lead.exists() and lead.company_id:
                return lead.company_id.id
        return self.env.company.id

    def action_apply(self):
        # Only the single-conversion wizard carries a user-chosen company; the
        # mass wizard (a different model) keeps Odoo's default behaviour.
        if self._name == "crm.lead2opportunity.partner" and self.company_id:
            leads = self.env["crm.lead"].browse(self.env.context.get("active_ids", []))
            for lead in leads:
                vals = {"company_id": self.company_id.id}
                # A sales team belongs to a company; drop it if it no longer
                # matches, so conversion doesn't fail on a cross-company team.
                if lead.team_id and lead.team_id.company_id and lead.team_id.company_id != self.company_id:
                    vals["team_id"] = False
                lead.write(vals)
        return super().action_apply()
