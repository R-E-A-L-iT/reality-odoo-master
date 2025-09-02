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

        # Current user (creator)
        creator = self.env.user

        # Only for internal users who opted in, and who have a valid email
        is_internal = creator.has_group("base.group_user")
        if is_internal and creator.leica_lead_reminder and creator.email:
            template = self.env.ref(
                "pro_crm_lead_leica_reminder.mail_template_crm_lead_leica_reminder",
                raise_if_not_found=False,
            )
            if template:
                # Send one email per lead created, to the creator’s email only
                for lead in leads:
                    # Ensure no follower/partner leakage: override recipients completely
                    email_values = {
                        "email_to": creator.email,
                        "recipient_ids": [],       # do not send to partners/followers
                        "partner_ids": [],         # do not auto-add partners
                    }
                    # Respect user language if set
                    ctx = {
                        "lang": creator.lang or self.env.lang,
                        "default_email_layout_xmlid": "mail.mail_notification_paynow",  # optional; Odoo still applies default layout without this
                    }
                    template.with_context(ctx).send_mail(
                        lead.id,
                        email_values=email_values,
                        force_send=True,
                    )

        return leads