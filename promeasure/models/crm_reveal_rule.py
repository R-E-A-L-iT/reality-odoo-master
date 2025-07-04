from odoo import models

class CrmRevealRule(models.Model):
    _inherit = 'crm.reveal.rule'

    def _create_lead_from_response(self, result):
        # call the parent class function, which creates the lead
        lead = super()._create_lead_from_response(result)
        if not lead:
            return False

        # match website.visitor records based on visitor id

        # find the crm.reveal.view (it hasn't been unlinked yet)
        view = self.env['crm.reveal.view'].search([
            ('reveal_ip', '=', result.get('ip')),
        ], order='create_date desc', limit=1)

        # if that view had a visitor, link the new lead to them
        if view and view.visitor_id:
            # write into the lead_ids M2M field on visitor
            view.visitor_id.sudo().write({
                'lead_ids': [(4, lead.id)]
            })
            lead.sudo().write({
                'visitor_ids': [(4, view.visitor_id.id)]
            })

        return lead
