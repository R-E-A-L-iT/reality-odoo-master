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

LEICA_MEDIA_CATEGORY_SEL = [
    ("film_vfx", "Film / VFX"),
    ("theme_parks", "Theme Parks / Rigging"),
    ("art_docs", "Art / Documentaries"),
]
LEICA_MEDIA_CATEGORY_LABEL = dict(LEICA_MEDIA_CATEGORY_SEL)

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
    leica_registration_date = fields.Datetime(
        string="Leica Registration Date",
        readonly=True,
        help="When the Leica lead log request email was sent."
    )
    leica_registration_error = fields.Text(
        string="Last Leica Registration Error",
        readonly=True,
        help="Error returned by the last failed registration attempt. Cleared on success."
    )

    leica_can_register = fields.Boolean(
        string="Ready for Leica Registration",
        compute="_compute_leica_can_register",
        store=False,
    )
    leica_missing_summary = fields.Char(
        string="Missing for Leica Registration",
        compute="_compute_leica_can_register",
        store=False,
        help="Human-readable list of what still needs to be filled in before "
             "this lead can be registered with Leica."
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
    leica_blk_arc_carrier = fields.Char(
        string="BLK ARC Carrier Type",
        help="Required by Leica when Product Interest is BLK ARC: the carrier type "
             "the end user wants to integrate BLK ARC onto."
    )
    leica_media_category = fields.Selection(
        selection=LEICA_MEDIA_CATEGORY_SEL,
        string="Media & Entertainment Category",
        help="Asked by the Leica portal when Market Segment is Media & Entertainment."
    )
    leica_discussion_notes = fields.Text(
        string="Discussion Notes",
        help="Sent to the Leica portal's Discussion Notes field. If the lead is part "
             "of an RFP, Leica asks for end-user contact info here."
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

    @api.depends("country_id", "partner_id.country_id")
    def _compute_leica_sales_region(self):
        for lead in self:
            country = lead.partner_id.country_id or lead.country_id
            code = (country.code or "").upper()
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
                    ("name", "=", "R-E-A-L.iT Solutions FL L.L.C.")
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

    def _leica_get_contact_names(self):
        """Return (first, last) for the Leica portal, preferring the partner's
        first_name/last_name fields (procontact). Falls back to splitting the
        lead-level contact name when no partner is linked yet."""
        self.ensure_one()
        partner = self.partner_id
        if partner and (partner.first_name or "").strip() and (partner.last_name or "").strip():
            return (partner.first_name.strip(), partner.last_name.strip())
        parts = (self.contact_name or "").strip().split()
        if len(parts) < 2:
            return (parts[0] if parts else "", "")
        return (parts[0], " ".join(parts[1:]))

    def _leica_missing_requirements(self):
        """Return a list of human-readable strings describing everything still
        missing before this lead can be registered on the Leica portal.
        Empty list == ready to register."""
        self.ensure_one()
        missing = []

        first, last = self._leica_get_contact_names()
        if not first or not last:
            missing.append(_("Contact first and last name"))
        if not (self.partner_name or "").strip():
            missing.append(_("Company name"))

        email_ok = bool(
            self.email_from
            and tools.email_normalize(self.email_from)
            and tools.single_email_re.match((self.email_from or "").strip())
        )
        if not email_ok:
            missing.append(_("Valid contact email"))

        digits = re.sub(r"\D", "", self.phone or "")
        if len(digits) < 7:
            missing.append(_("Valid contact phone"))

        partner = self.partner_id
        if not partner:
            missing.append(_("Linked customer (contact record) with a full address"))
        else:
            if not (partner.street or "").strip():
                missing.append(_("Customer street address"))
            if not (partner.city or "").strip():
                missing.append(_("Customer city"))
            if not partner.state_id:
                missing.append(_("Customer state/province"))
            if not (partner.zip or "").strip():
                missing.append(_("Customer ZIP/postal code"))

        country = (partner.country_id if partner else False) or self.country_id
        if (country.code or "").upper() not in ("CA", "US"):
            missing.append(_("Customer country must be Canada or United States"))

        if not (self.website or "").strip():
            missing.append(_("Company website"))
        if not self.leica_market_segment:
            missing.append(_("Leica market segment"))
        if not self.leica_product_interest:
            missing.append(_("Leica product interest"))
        if self.leica_product_interest == "blk_arc" and not (self.leica_blk_arc_carrier or "").strip():
            missing.append(_("BLK ARC carrier type (required for BLK ARC product interest)"))
        if not self.leica_quantity or self.leica_quantity <= 0:
            missing.append(_("Quantity (must be greater than zero)"))
        if not self.date_deadline:
            missing.append(_("Expected purchase date (Expected Closing)"))

        return missing

    # can the lead be registered with leica
    @api.depends(
        "contact_name", "partner_name", "email_from", "phone", "website",
        "partner_id.name", "partner_id.street", "partner_id.city", "partner_id.state_id",
        "partner_id.zip", "partner_id.country_id", "country_id",
        "leica_market_segment", "leica_product_interest", "leica_blk_arc_carrier",
        "leica_quantity", "date_deadline",
    )
    def _compute_leica_can_register(self):
        for lead in self:
            missing = lead._leica_missing_requirements()
            lead.leica_can_register = not missing
            lead.leica_missing_summary = "; ".join(missing)

    # lead log values grouped by section for the email: [(section, [(label, value)])]
    def _leica_lead_log_sections(self, data):
        self.ensure_one()
        region = {"ca": "Canada", "us": "United States"}.get(data["sales_region"], "")
        state = data["state_name"]
        if state and data["state_code"]:
            state = "%s (%s)" % (state, data["state_code"])

        def yes_no(value):
            return "Yes" if value else "No"

        return [
            ("Lead", [
                ("Lead ID", data["lead_id"]),
                ("Lead Name", self.name),
                ("Odoo Link", "%s/web#id=%s&model=crm.lead&view_type=form" % (self.get_base_url(), self.id)),
                ("Sales Region", region),
                ("Market Segment", data["market_segment"]),
                ("Media & Entertainment Category", data["media_category"]),
                ("Product Interest", data["product_interest"]),
                ("BLK ARC Carrier Type", data["blk_arc_carrier"]),
                ("Quantity", data["quantity"]),
                ("Expected Purchase Date (MM/DD/YYYY)", data["expected_purchase_date"]),
                ("Part of an RFP", data["is_rfp"]),
            ]),
            ("Contact", [
                ("First Name", data["first_name"]),
                ("Last Name", data["last_name"]),
                ("Email", data["email"]),
                ("Phone", data["phone"]),
            ]),
            ("Company", [
                ("Company Name", data["company_name"]),
                ("Street", data["address"]),
                ("City", data["city"]),
                ("State/Province", state),
                ("ZIP/Postal Code", data["zip"]),
                ("Company Website", data["company_website"]),
            ]),
            ("End-user Requests", [
                ("Requested a Demonstration", yes_no(data["demo_requested"])),
                ("Requested Pricing", yes_no(data["pricing_requested"])),
                ("Requested a Meeting", yes_no(data["meeting_requested"])),
            ]),
            ("Discussion Notes", [
                ("Discussion Notes", data["discussion_notes"]),
            ]),
        ]

    def _leica_lead_log_body(self, data):
        cell = "padding:6px 12px;border:1px solid #dee2e6;vertical-align:top;"
        rows = Markup()
        for section, items in self._leica_lead_log_sections(data):
            rows += Markup(
                '<tr><th colspan="2" style="%sbackground:#f1f3f5;text-align:left;font-size:15px;">%s</th></tr>'
            ) % (cell, section)
            for label, value in items:
                if value in (False, None, ""):
                    value = "N/A"
                rows += Markup(
                    '<tr><td style="%sfont-weight:bold;white-space:nowrap;">%s</td><td style="%swhite-space:pre-wrap;">%s</td></tr>'
                ) % (cell, label, cell, value)
        return Markup(
            '<div style="font-family:Arial,sans-serif;font-size:14px;">'
            '<p>A new lead is ready to be logged with Leica.</p>'
            '<table style="border-collapse:collapse;">%s</table>'
            '</div>'
        ) % rows

    # email the lead log request; returns (ok, message)
    def _send_leica_lead_log_email(self, data):
        self.ensure_one()
        mail = self.env["mail.mail"].sudo().create({
            "subject": LEICA_LEAD_LOG_SUBJECT,
            "email_to": LEICA_LEAD_LOG_EMAIL,
            "email_from": self.env.user.email_formatted or self.env.company.email_formatted,
            "body_html": self._leica_lead_log_body(data),
            "auto_delete": False,
        })
        mail.send(raise_exception=False)

        if mail.state == "exception":
            reason = mail.failure_reason or _("unknown error")
            _logger.error("Leica lead log email for lead %s failed: %s", self.id, reason)
            return False, _("Could not send the Leica lead log email to %s: %s") % (LEICA_LEAD_LOG_EMAIL, reason)
        return True, _("Leica lead log request sent to %s.") % LEICA_LEAD_LOG_EMAIL

    @api.model
    def _fmt_leica_date(self, d):
        """mm/dd/yyyy, as the Leica portal expects."""
        if not d:
            return ""
        try:
            return fields.Date.to_date(d).strftime("%m/%d/%Y")
        except Exception:
            return ""

    def _leica_portal_data(self):
        """The exact values that will be typed into the Leica portal form.
        Single source of truth for both the confirmation wizard and the lead
        log email."""
        self.ensure_one()
        first, last = self._leica_get_contact_names()
        partner = self.partner_id
        state = partner.state_id if partner else False
        return {
            "lead_id": self.id,
            "sales_region": self.leica_sales_region or "",
            "market_segment": LEICA_MARKET_SEGMENT_LABEL.get(self.leica_market_segment, ""),
            "first_name": first,
            "last_name": last,
            "company_name": self.partner_name or "",
            "email": self.email_from or "",
            "phone": self.phone or "",
            "address": (partner.street or "") if partner else "",
            "city": (partner.city or "") if partner else "",
            "state_name": (state.name or "") if state else "",
            "state_code": (state.code or "") if state else "",
            "zip": (partner.zip or "") if partner else "",
            "company_website": self.website or "",
            "product_interest": LEICA_PRODUCT_INTEREST_LABEL.get(self.leica_product_interest, ""),
            "blk_arc_carrier": (self.leica_blk_arc_carrier or "") if self.leica_product_interest == "blk_arc" else "",
            "media_category": LEICA_MEDIA_CATEGORY_LABEL.get(self.leica_media_category, "") if self.leica_market_segment == "media_ent" else "",
            "quantity": str(self.leica_quantity or ""),
            "expected_purchase_date": self._fmt_leica_date(self.date_deadline),
            "is_rfp": "Yes" if self.leica_is_rfp else "No",
            "demo_requested": bool(self.leica_has_demo_request),
            "pricing_requested": bool(self.leica_has_pricing_request),
            "meeting_requested": bool(self.leica_has_meeting_request),
            "discussion_notes": self.leica_discussion_notes or "",
        }

    # opens the confirmation wizard; the wizard calls _leica_do_register()
    def action_leica_register(self):
        self.ensure_one()
        if self.leica_registered:
            raise UserError(_("This lead has already been registered with Leica."))
        missing = self._leica_missing_requirements()
        if missing:
            raise UserError(_(
                "This lead cannot be registered with Leica yet. Missing:\n- %s"
            ) % "\n- ".join(missing))
        return {
            "type": "ir.actions.act_window",
            "name": _("Confirm Leica Lead Registration"),
            "res_model": "leica.register.confirm.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_lead_id": self.id},
        }

    def _leica_do_register(self):
        """Email the lead log request. Called by the confirmation wizard.
        Returns a display_notification client action; never raises after the
        attempt so failure state survives in the database."""
        self.ensure_one()
        if self.leica_registered:
            raise UserError(_("This lead has already been registered with Leica."))
        missing = self._leica_missing_requirements()
        if missing:
            raise UserError(_(
                "This lead cannot be registered with Leica yet. Missing:\n- %s"
            ) % "\n- ".join(missing))

        ok, message = self._send_leica_lead_log_email(self._leica_portal_data())

        system_partner = self.env.ref("base.user_root").partner_id
        if ok:
            self.write({
                "leica_registered": True,
                "leica_registration_date": fields.Datetime.now(),
                "leica_registration_error": False,
            })
            self.message_post(
                body=message,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
                author_id=system_partner.id,
            )
        else:
            self.write({"leica_registration_error": message})
            self.message_post(
                body=_("Leica lead registration FAILED: %s") % message,
                message_type="comment",
                subtype_xmlid="mail.mt_note",
                author_id=system_partner.id,
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Leica Registration") if ok else _("Leica Registration Failed"),
                "message": message,
                "type": "success" if ok else "danger",
                "sticky": not ok,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
