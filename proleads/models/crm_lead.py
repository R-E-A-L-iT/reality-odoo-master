import re
import logging

from markupsafe import Markup

from odoo import fields, models, api, _, tools
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

LEICA_LEAD_LOG_EMAIL = "grokbot@r-e-a-l.it"
LEICA_LEAD_LOG_SUBJECT = "Leica lead log request"

LEICA_MARKET_SEGMENT_SEL = [
    ("bld_construction", "Building & Construction"),
    ("heavy_construction", "Heavy Construction"),
    ("industrial_plant", "Industrial Plant"),
    ("media_ent", "Media & Entertainment"),
    ("public_safety", "Public Safety"),
    ("rail", "Rail"),
    ("surveying_ground", "Surveying Ground"),
]
LEICA_MARKET_SEGMENT_LABEL = dict(LEICA_MARKET_SEGMENT_SEL)

LEICA_PRODUCT_INTEREST_SEL = [
    ("blk_arc", "BLK ARC"),
    ("rtc_pxx_2go_2fly", "RTC/Pxx/2GO/2FLY"),
    ("trk_100_500_700", "TRK 100/500/700"),
]
LEICA_PRODUCT_INTEREST_LABEL = dict(LEICA_PRODUCT_INTEREST_SEL)

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    opportunity_log = fields.Datetime(string="Opportunity Log", help="Timestamp of when this lead was converted to an opportunity.")
    opportunity_answer_date = fields.Date(string="Opportunity Answer Date", help="Date when the lead was accepted or rejected as an opportunity.")

    leica_registered = fields.Boolean(
        string="Registered with Leica",
        default=False,
        readonly=True,
        help="Set automatically after the 'Register with Leica' lead log request email is sent."
    )

    leica_can_register = fields.Boolean(
        string="Ready for Leica Registration",
        compute="_compute_leica_can_register",
        store=False,
    )

    leica_market_segment = fields.Selection(
        selection=LEICA_MARKET_SEGMENT_SEL,
        string="Leica Market Segment",
        help="Required by Leica lead portal."
    )
    leica_product_interest = fields.Selection(
        selection=LEICA_PRODUCT_INTEREST_SEL,
        string="Leica Product Interest",
        help="Required by Leica lead portal."
    )
    leica_is_rfp = fields.Boolean(
        string="Is this lead part of an RFP?"
    )

    leica_sales_region = fields.Selection(
        selection=[("ca", "Canada"), ("us", "United States")],
        string="Leica Sales Region",
        compute="_compute_leica_sales_region",
        store=True,
        readonly=True,
        help="Auto-derived from country (CA→Canada, US→United States)."
    )

    # leica_expected_purchase_date = fields.Date(string="Expected Purchase Date")
    leica_quantity = fields.Integer(string="Quantity")

    leica_has_demo_request = fields.Boolean(string="Has the end-user requested a demonstration?")
    leica_has_pricing_request = fields.Boolean(string="Has the end-user requested pricing?")
    leica_has_meeting_request = fields.Boolean(string="Has the end-user requested a meeting?")

    leica_representative_id = fields.Many2one('res.partner', string="Leica Representative", help="Leica representative associated with this lead.")

    partner_street = fields.Char(related='partner_id.street', string="Street (Partner)")
    partner_city = fields.Char(related='partner_id.city', string="City (Partner)")
    partner_zip = fields.Char(related='partner_id.zip', string="ZIP/Postal (Partner)")
    partner_state_id = fields.Many2one('res.country.state', related='partner_id.state_id', string="State/Province (Partner)")
    partner_country_id = fields.Many2one('res.country', related='partner_id.country_id', string="Country (Partner)")

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

    partner_company_id = fields.Many2one('res.partner', string="Company (Partner)", help="Company associated with the partner.")
    opportunity_notes = fields.Text(string="Opportunity Notes")
    linkedin_link = fields.Char('LinkedIn Link')
    quotation_amount = fields.Float(compute="_compute_total_quotation_amount")

    ba_email_subject = fields.Char(
        string='Email Subject',
        help='Custom subject used when sending emails from this opportunity.',
    )

    def _message_compute_subject(self):
        self.ensure_one()
        if self.ba_email_subject:
            return self.ba_email_subject
        return super()._message_compute_subject()

    @api.depends("country_id")
    def _compute_leica_sales_region(self):
        for lead in self:
            code = (lead.country_id.code or "").upper()
            if code == "CA":
                lead.leica_sales_region = "ca"
            elif code == "US":
                lead.leica_sales_region = "us"
            else:
                lead.leica_sales_region = False

    @api.model
    def _company_for_country_code(self, code):
        """Return target res.company for a 2-letter country code."""
        if not code:
            return self.env['res.company']
        code = code.upper()

        ICP = self.env["ir.config_parameter"].sudo()
        company_id = False

        # Optional: allow overriding via system parameters (technical > system params)
        #   procrm_auto_company_from_visitor.ca_company_id
        #   procrm_auto_company_from_visitor.us_company_id
        if code == "CA":
            company_id = int(ICP.get_param(
                "procrm_auto_company_from_visitor.ca_company_id", "0") or 0
            )
            if not company_id:
                company_id = self.env["res.company"].sudo().search([
                    ("name", "=", "R-E-A-L.iT Solutions")
                ], limit=1).id
        elif code == "US":
            company_id = int(ICP.get_param(
                "procrm_auto_company_from_visitor.us_company_id", "0") or 0
            )
            if not company_id:
                company_id = self.env["res.company"].sudo().search([
                    ("name", "=", "R-E-A-L.iT U.S. Inc.")
                ], limit=1).id

        return self.env["res.company"].browse(company_id) if company_id else self.env["res.company"]

    def _apply_stage_probability_override(self, stage):
        """Return float or None. Only applies to opportunities."""
        self.ensure_one()
        if self.type != 'opportunity':
            return None
        if stage and stage.use_probability_override:
            return stage.probability_override
        return None

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)

        for lead in leads:
            new_prob = lead._apply_stage_probability_override(lead.stage_id)
            if new_prob is not None:
                # write instead of direct set to trigger relevant onchange/computes safely
                lead.write({"probability": new_prob})

        # Process each created lead alongside its original vals (order preserved)
        for lead, vals in zip(leads, vals_list):
            try:
                # Only consider leads originating from website
                comes_from_website = bool(
                    vals.get("website_id")
                    or getattr(lead, "website_id", False)
                )
                if not comes_from_website:
                    continue

                # Gather related visitors robustly (handles either visitor_id or visitor_ids)
                Visitor = self.env["website.visitor"].sudo()
                visitors = Visitor.browse()
                if hasattr(lead, "visitor_ids") and lead.visitor_ids:
                    visitors |= lead.visitor_ids
                if hasattr(lead, "visitor_id") and lead.visitor_id:
                    visitors |= lead.visitor_id
                if vals.get("visitor_id"):
                    visitors |= Visitor.browse(vals["visitor_id"])

                if not visitors:
                    # No known visitor relation → nothing to do
                    continue

                # Determine the most common non-empty country code across visitors
                codes = [v.country_id.code for v in visitors if v.country_id and v.country_id.code]
                if not codes:
                    continue
                code = max(set(codes), key=codes.count)

                # Map country code → company
                target_company = lead._company_for_country_code(code)
                if not target_company:
                    continue

                # If current company differs, switch it.
                # Clear conflicting team if it belongs to a different company.
                vals_to_write = {"company_id": target_company.id}
                if lead.team_id and lead.team_id.company_id and lead.team_id.company_id != target_company:
                    vals_to_write["team_id"] = False

                # Use sudo to avoid multi-company write restrictions at creation time.
                lead.sudo().write(vals_to_write)

                _logger.info(
                    "Auto-assigned lead %s to company %s based on visitor country %s",
                    lead.id, target_company.display_name, code
                )

            except Exception as e:
                _logger.exception("Auto company from visitor failed for lead %s: %s", lead.id, e)

        return leads

    def write(self, vals):
        if 'stage_id' not in vals:
            return super().write(vals)

        # Apply per-record to respect each record's target stage
        for lead in self:
            per_vals = dict(vals)
            # Determine the stage that will be applied to this specific record
            target_stage = None
            if 'stage_id' in per_vals and per_vals['stage_id']:
                target_stage = self.env['crm.stage'].browse(per_vals['stage_id'])
            else:
                target_stage = lead.stage_id

            new_prob = lead._apply_stage_probability_override(target_stage)
            if new_prob is not None:
                per_vals['probability'] = new_prob

            super(CrmLead, lead).write(per_vals)
        return True

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

    # can the lead be registered with leica
    @api.depends("contact_name", "partner_name", "email_from", "phone", "partner_id.street", "partner_id.city", "partner_id.zip", "partner_id.country_id")
    def _compute_leica_can_register(self):
        single_re = tools.single_email_re
        for lead in self:
            has_core = bool(lead.contact_name and lead.partner_name and lead.email_from and lead.phone)
            email_ok = bool(lead.email_from and tools.email_normalize(lead.email_from) and single_re.match(lead.email_from.strip() or ""))
            # basic phone sanity (7+ digits)
            phone_ok = False
            if lead.phone:
                digits = re.sub(r"\D", "", lead.phone)
                phone_ok = len(digits) >= 7

            addr_ok = bool(
                lead.partner_id and
                (lead.partner_id.street or "").strip() and
                (lead.partner_id.city or "").strip() and
                (lead.partner_id.zip or "").strip() and
                lead.partner_id.country_id
            )

            lead.leica_can_register = has_core and email_ok and phone_ok and addr_ok

    # values required for the leica lead log, grouped by section: [(section, [(label, value)])]
    def _leica_lead_log_sections(self):
        self.ensure_one()
        partner = self.partner_id
        state = partner.state_id
        country_code = (partner.country_id.code or "").upper()
        rep = self.leica_representative_id

        def yes_no(value):
            return "Yes" if value else "No"

        return [
            ("Lead", [
                ("Lead ID", self.id),
                ("Lead Name", self.name),
                ("Odoo Link", "%s/web#id=%s&model=crm.lead&view_type=form" % (self.get_base_url(), self.id)),
                ("Leica Representative", rep.email and "%s <%s>" % (rep.name, rep.email) or rep.name),
            ]),
            ("Contact", [
                ("Contact Name", self.contact_name),
                ("Company Name", self.partner_name),
                ("Email", self.email_from),
                ("Phone", self.phone),
            ]),
            ("Address", [
                ("Street", partner.street),
                ("City", partner.city),
                ("State/Province", state.code or state.name),
                ("ZIP/Postal Code", partner.zip),
                ("Country", partner.country_id.name),
                ("Sales Region", {"CA": "Canada", "US": "United States"}.get(country_code)),
            ]),
            ("Leica Details", [
                ("Market Segment", LEICA_MARKET_SEGMENT_LABEL.get(self.leica_market_segment)),
                ("Product Interest", LEICA_PRODUCT_INTEREST_LABEL.get(self.leica_product_interest)),
                ("Part of an RFP", yes_no(self.leica_is_rfp)),
                ("Expected Purchase Date (MM/DD/YYYY)", self.date_deadline and self.date_deadline.strftime("%m/%d/%Y")),
                ("Quantity", self.leica_quantity),
            ]),
            ("End-user Requests", [
                ("Requested a Demonstration", yes_no(self.leica_has_demo_request)),
                ("Requested Pricing", yes_no(self.leica_has_pricing_request)),
                ("Requested a Meeting", yes_no(self.leica_has_meeting_request)),
            ]),
        ]

    def _leica_lead_log_body(self):
        cell = "padding:6px 12px;border:1px solid #dee2e6;vertical-align:top;"
        rows = Markup()
        for section, items in self._leica_lead_log_sections():
            rows += Markup(
                '<tr><th colspan="2" style="%sbackground:#f1f3f5;text-align:left;font-size:15px;">%s</th></tr>'
            ) % (cell, section)
            for label, value in items:
                if value in (False, None, ""):
                    value = "N/A"
                rows += Markup(
                    '<tr><td style="%sfont-weight:bold;white-space:nowrap;">%s</td><td style="%s">%s</td></tr>'
                ) % (cell, label, cell, value)
        return Markup(
            '<div style="font-family:Arial,sans-serif;font-size:14px;">'
            '<p>A new lead is ready to be logged with Leica.</p>'
            '<table style="border-collapse:collapse;">%s</table>'
            '</div>'
        ) % rows

    # register lead with leica by emailing a lead log request
    def action_leica_register(self):
        self.ensure_one()
        if self.leica_registered:
            raise UserError(_("This lead has already been registered with Leica."))

        mail = self.env["mail.mail"].sudo().create({
            "subject": LEICA_LEAD_LOG_SUBJECT,
            "email_to": LEICA_LEAD_LOG_EMAIL,
            "email_from": self.env.user.email_formatted or self.env.company.email_formatted,
            "body_html": self._leica_lead_log_body(),
            "auto_delete": False,
        })
        # raise so a delivery failure rolls back and the lead can be retried
        mail.send(raise_exception=True)

        self.leica_registered = True
        system_partner = self.env.ref("base.user_root").partner_id
        self.message_post(
            body=_("Leica lead log request sent to %s.", LEICA_LEAD_LOG_EMAIL),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=system_partner.id,
        )
