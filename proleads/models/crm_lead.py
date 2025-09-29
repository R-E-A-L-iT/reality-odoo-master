import re
import json
import logging
import requests
import hmac
import hashlib

from odoo import fields, models, api, _, tools
from odoo.exceptions import UserError

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

    @api.model_create_multi
    def create(self, vals_list):
        leads = super().create(vals_list)

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
    @api.depends("contact_name", "partner_name", "email_from", "phone",
                 "leica_market_segment", "leica_product_interest", "leica_sales_region")
    def _compute_leica_can_register(self):
        single_re = tools.single_email_re
        for lead in self:
            has_all = bool(lead.contact_name and lead.partner_name and lead.email_from and lead.phone)
            email_ok = False
            if lead.email_from:
                email_ok = bool(tools.email_normalize(lead.email_from)) and bool(single_re.match(lead.email_from.strip()))
            phone_ok = False
            if lead.phone:
                digits = re.sub(r"\D", "", lead.phone)
                phone_ok = len(digits) >= 7

            seg_ok = bool(lead.leica_market_segment)
            prod_ok = bool(lead.leica_product_interest)
            region_ok = bool(lead.leica_sales_region)

            lead.leica_can_register = has_all and email_ok and phone_ok and seg_ok and prod_ok and region_ok


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
        if not self.leica_can_register:
            raise UserError(_("Please complete all required Leica fields before registering."))

        payload = {
            "lead_id": self.id,
            "contact_name": self.contact_name or "",
            "company_name": self.partner_name or "",
            "email": self.email_from or "",
            "phone": self.phone or "",

            # --- Leica additions in payload ---
            "market_segment_code": self.leica_market_segment or "",
            "market_segment_label": LEICA_MARKET_SEGMENT_LABEL.get(self.leica_market_segment or "", ""),
            "product_interest_code": self.leica_product_interest or "",
            "product_interest_label": LEICA_PRODUCT_INTEREST_LABEL.get(self.leica_product_interest or "", ""),
            "is_rfp": bool(self.leica_is_rfp),
            "sales_region": self.leica_sales_region or "",  # 'ca' or 'us'

            # useful extras you already had
            "opportunity_source": self.opportunity_source or "",
            "opportunity_sn": self.opportunity_sn or "",
            "opportunity_notes": self.opportunity_notes or "",
            "quotation_amount": self.quotation_amount or 0.0,
            "odoo_company": self.company_id.name if self.company_id else "",
            "odoo_lead_url": self.get_portal_url() if hasattr(self, "get_portal_url") else "",
        }

        self._post_to_leica_webhook(payload)

        self.leica_registered = True
        system_partner = self.env.ref("base.user_root").partner_id
        self.message_post(
            body=_("Lead was sent to Leica webhook and is awaiting approval."),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=system_partner.id,
        )
        return True