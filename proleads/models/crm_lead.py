from odoo import fields, models, api, tools

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    opportunity_source = fields.Selection([
        ("source_website", "Website"),
        ("source_landing", "Landing Page"),
        ("source_linkedin", "LinkedIn"),
        ("source_social", "Other Social Platforms"),
        ("source_email", "Email Campaign"),
        ("source_trade", "Tradeshow"),
        ("source_other", "Other Source"),
        ],
        string="Opportunity Source")

    opportunity_sn = fields.Char(
        string="Opportunity SN"
    )

    opportunity_custom_status = fields.Selection(
        [
            ("pending", "Pending"), 
            ("accepted", "Accepted"), 
            ("rejected", "Rejected")
        ], 
        string="Opportunity Status", 
        default=False
    )

    opportunity_notes = fields.Text(string="Opportunity Notes")
    linkedin_link = fields.Char('LinkedIn Link')
    quotation_amount = fields.Float(compute="_compute_total_quotation_amount")

    def _compute_total_quotation_amount(self):
        for lead in self:
            sale_orders = lead.order_ids.filtered_domain(lead._get_action_view_sale_quotation_domain())
            total_amount = sum(order.amount_untaxed for order in sale_orders)
            if total_amount:
                lead.quotation_amount = total_amount
                lead.expected_revenue = total_amount
            else:
                lead.quotation_amount = 0.00
                lead.expected_revenue = 0.00

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)

        creator = self.env.user
        is_internal = creator.has_group("base.group_user")

        if is_internal and creator.leica_lead_reminder and creator.email and creator.partner_id:
            lang = creator.lang or self.env.lang
            for lead in leads:
                subject = f"Reminder: Log “{lead.name}” in the Leica portal"
                body = (
                    "<p>Hello,</p>"
                    f"<p>This is a reminder to log the lead "
                    f"<strong>{tools.html_escape(lead.name or '')}</strong> in the Leica portal.</p>"
                    "<p>Thanks.</p>"
                )
                
                lead.with_context(lang=lang).message_notify(
                    subject=subject,
                    body=body,
                    partner_ids=[creator.partner_id.id],
                    email_layout_xmlid="mail.mail_notification_light",
                    email_add_signature=False,
                )

        return leads