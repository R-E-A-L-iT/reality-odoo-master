# -*- coding: utf-8 -*-

import re
import json
import logging
import requests
import hmac
import hashlib
from odoo import fields, models, api, _, tools
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

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
        help="Set automatically after the 'Register with Leica' action is sent."
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

    # helper for compiling/sending information to leica webhook
    def _post_to_leica_webhook(self, payload: dict):
        ICP = self.env["ir.config_parameter"].sudo()
        url = ICP.get_param("proleads_leica_webhook_url", "").strip()
        secret = ICP.get_param("proleads_leica_webhook_secret", "").strip()

        if not url:
            raise UserError(_("Leica webhook URL is not configured (proleads_leica_webhook_url)."))
        if not secret:
            raise UserError(_("Leica webhook secret is not configured (proleads_leica_webhook_secret)."))

        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

        headers = {
            "Content-Type": "application/json",
            "X-REAL-Signature": signature,
            "User-Agent": "Odoo-17/LeicaWebhook",
        }

        try:
            resp = requests.post(url, data=body, headers=headers, timeout=10)
        except requests.RequestException as e:
            _logger.exception("Error posting to Leica webhook: %s", e)
            raise UserError(_("Failed to reach the Leica webhook: %s") % e) from e

        if resp.status_code != 200:
            _logger.error("Leica webhook non-200: %s, body=%s", resp.status_code, resp.text[:500])
            raise UserError(_("Leica webhook responded with HTTP %s") % resp.status_code)

        try:
            data = resp.json()
        except Exception:
            _logger.error("Leica webhook invalid JSON response: %s", resp.text[:500])
            raise UserError(_("Leica webhook returned invalid JSON."))

        if not data or not data.get("ok"):
            _logger.error("Leica webhook returned error payload: %s", data)
            raise UserError(_("Leica webhook indicated failure."))

        return True

    # register lead with leica sending email to vm
    def action_leica_register(self):
        self.ensure_one()
        if self.leica_registered:
            raise UserError(_("This lead has already been registered with Leica."))

        def _fmt_us_date(d):
            if not d:
                return ""
            try:
                py = fields.Date.to_date(d)
                return py.strftime("%m/%d/%Y")
            except Exception:
                return ""

        sales_region = ""
        c = (self.partner_id.country_id and self.partner_id.country_id.code or "").upper()
        if c == "CA":
            sales_region = "ca"
        elif c == "US":
            sales_region = "us"

        payload = {
            "lead_id": self.id,
            "contact_name": self.contact_name or "",
            "company_name": self.partner_name or "",
            "email": self.email_from or "",
            "phone": self.phone or "",

            "street": self.partner_id.street or "",
            "city": self.partner_id.city or "",
            "state": (self.partner_id.state_id and (self.partner_id.state_id.code or self.partner_id.state_id.name)) or "",
            "zip": self.partner_id.zip or "",
            "country": (self.partner_id.country_id and self.partner_id.country_id.name) or "",

            "sales_region": sales_region,

            "market_segment_label": dict(self._fields['leica_market_segment'].selection).get(self.leica_market_segment, "") if hasattr(self, 'leica_market_segment') else "",
            "product_interest_label": dict(self._fields['leica_product_interest'].selection).get(self.leica_product_interest, "") if hasattr(self, 'leica_product_interest') else "",
            "is_rfp": bool(getattr(self, 'leica_is_rfp', False)),

            "expected_closing_mmddyyyy": _fmt_us_date(self.date_deadline),
            "quantity": self.leica_quantity or None,

            "has_demo_request": bool(self.leica_has_demo_request),
            "has_pricing_request": bool(self.leica_has_pricing_request),
            "has_meeting_request": bool(self.leica_has_meeting_request),
        }

        self._post_to_leica_webhook(payload)

        self.leica_registered = True
        system_partner = self.env.ref("base.user_root").partner_id
        self.message_post(
            body=_("Lead has been registered in Leica's system and is awaiting approval."),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=system_partner.id,
        )
