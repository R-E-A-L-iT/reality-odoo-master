# -*- coding: utf-8 -*-
import re
import json
import base64
import logging
from datetime import datetime, timedelta
from markupsafe import Markup, escape

import os
import mimetypes
from urllib.parse import urlparse

import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class QuoCall(models.Model):
    _name = "quo.call"
    _description = "Quo Call"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "started_at desc, id desc"

    name = fields.Char(string="Display Name", compute="_compute_name", store=False)

    quo_call_id = fields.Char(string="Quo Call ID", required=True, index=True)
    phone_number_id = fields.Char(string="Phone Number ID", index=True)
    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound"), ("unknown", "Unknown")],
        default="unknown",
        string="Direction",
        index=True,
    )

    started_at = fields.Datetime(string="Started At", index=True)
    ended_at = fields.Datetime(string="Ended At", index=True)
    duration_seconds = fields.Integer(string="Duration (s)")

    # Raw payloads for traceability
    participants_json = fields.Text(string="Participants (JSON)")
    contact_ids_json = fields.Text(string="Contact IDs (JSON)")
    raw_call_json = fields.Text(string="Raw Call (JSON)")

    transcript_id = fields.One2many("quo.call.transcript", "call_id", string="Transcripts")

    from_number = fields.Char(string="From")
    to_number = fields.Char(string="To")

    from_sanitized = fields.Char(string="From (sanitized)", index=True)
    to_sanitized = fields.Char(string="To (sanitized)", index=True)

    partner_ids = fields.Many2many(
        "res.partner",
        "quo_call_res_partner_rel",
        "call_id",
        "partner_id",
        string="Participants",
    )

    caller_from_partner_id = fields.Many2one(
        "res.partner",
        string="Caller (From)",
        readonly=True,
        index=True,
    )

    caller_to_partner_id = fields.Many2one(
        "res.partner",
        string="Caller (To)",
        readonly=True,
        index=True,
    )

    _sql_constraints = [
        ("quo_call_id_unique", "unique(quo_call_id)", "Quo Call ID must be unique."),
    ]

    # ------------------------------------------------------------------
    # Smart-button counts (related quotes & opportunities)
    # ------------------------------------------------------------------
    quote_count = fields.Integer(
        string="Quotes",
        compute="_compute_related_record_counts",
    )
    opportunity_count = fields.Integer(
        string="Opportunities",
        compute="_compute_related_record_counts",
    )

    @api.depends("partner_ids", "caller_from_partner_id", "caller_to_partner_id")
    def _compute_related_record_counts(self):
        for call in self:
            external = call._get_external_partners()
            if not external:
                call.quote_count = 0
                call.opportunity_count = 0
                continue

            partner_ids = external.ids
            commercial_ids = list({p.commercial_partner_id.id for p in external})
            all_ids = list(set(partner_ids + commercial_ids))

            call.quote_count = self.env["sale.order"].sudo().search_count([
                ("state", "in", ["draft", "sent"]),
                "|", "|", "|",
                    ("partner_id", "in", all_ids),
                    ("partner_shipping_id", "in", all_ids),
                    ("partner_invoice_id", "in", all_ids),
                    ("message_partner_ids", "in", partner_ids),
            ])
            call.opportunity_count = self.env["crm.lead"].sudo().search_count([
                ("type", "=", "opportunity"),
                ("active", "=", True),
                "|",
                    ("partner_id", "in", all_ids),
                    ("message_partner_ids", "in", partner_ids),
            ])

    def action_view_related_quotes(self):
        self.ensure_one()
        external = self._get_external_partners()
        partner_ids = external.ids
        commercial_ids = list({p.commercial_partner_id.id for p in external})
        all_ids = list(set(partner_ids + commercial_ids))
        return {
            "type": "ir.actions.act_window",
            "name": "Related Quotes",
            "res_model": "sale.order",
            "view_mode": "tree,form",
            "domain": [
                ("state", "in", ["draft", "sent"]),
                "|", "|", "|",
                    ("partner_id", "in", all_ids),
                    ("partner_shipping_id", "in", all_ids),
                    ("partner_invoice_id", "in", all_ids),
                    ("message_partner_ids", "in", partner_ids),
            ],
        }

    def action_view_related_opportunities(self):
        self.ensure_one()
        external = self._get_external_partners()
        partner_ids = external.ids
        commercial_ids = list({p.commercial_partner_id.id for p in external})
        all_ids = list(set(partner_ids + commercial_ids))
        return {
            "type": "ir.actions.act_window",
            "name": "Related Opportunities",
            "res_model": "crm.lead",
            "view_mode": "tree,form",
            "domain": [
                ("type", "=", "opportunity"),
                ("active", "=", True),
                "|",
                    ("partner_id", "in", all_ids),
                    ("message_partner_ids", "in", partner_ids),
            ],
        }

    # ----- Summary -----
    summary_text = fields.Text(string="Summary", readonly=True)
    next_steps_text = fields.Text(string="Next Steps", readonly=True)
    raw_summary_json = fields.Text(string="Raw Summary (JSON)", readonly=True)

    # ----- Recording -----
    recording_url = fields.Char(string="Recording URL", readonly=True)
    recording_mimetype = fields.Char(string="Recording MIME Type", readonly=True)
    recording_duration_seconds = fields.Integer(string="Recording Duration (s)", readonly=True)
    raw_recording_json = fields.Text(string="Raw Recording (JSON)", readonly=True)

    @api.model
    def _sanitize_phone(self, phone):
        """Very tolerant phone sanitizer: keep digits, preserve leading + if present, else add + if looks like E.164."""
        if not phone:
            return False
        s = str(phone).strip()
        has_plus = s.startswith("+")
        digits = re.sub(r"\D+", "", s)
        if not digits:
            return False
        # keep the plus if it was present
        if has_plus:
            return "+" + digits
        # if it looks like country+number length, normalize with +
        if len(digits) >= 10:
            return "+" + digits
        return digits

    @api.model
    def _normalize_direction(self, raw):
        """
        QUO can send incoming/outgoing, inbound/outbound, etc.
        Normalize to our selection: inbound/outbound/unknown
        """
        s = (raw or "").strip().lower()
        if s in ("inbound", "incoming", "in"):
            return "inbound"
        if s in ("outbound", "outgoing", "out"):
            return "outbound"
        return "unknown"

    @api.depends(
        "direction",
        "from_number",
        "to_number",
        "caller_from_partner_id",
        "caller_to_partner_id",
        "caller_from_partner_id.name",
        "caller_to_partner_id.name",
    )
    def _compute_name(self):
        for rec in self:
            prefix = "Call"
            if rec.direction == "inbound":
                prefix = "Inbound"
            elif rec.direction == "outbound":
                prefix = "Outbound"

            from_label = (rec.caller_from_partner_id.name or "").strip() if rec.caller_from_partner_id else ""
            to_label = (rec.caller_to_partner_id.name or "").strip() if rec.caller_to_partner_id else ""

            if not from_label:
                from_label = rec.from_number or ""
            if not to_label:
                to_label = rec.to_number or ""

            rec.name = f"{prefix} call from {from_label} to {to_label}".strip()

    def _quo_sync_phone_numbers(self):
        """Fetch Quo phone numbers and upsert into quo.phone.number."""
        payload = self._quo_get("phone-numbers")
        data = payload.get("data") if isinstance(payload, dict) else []
        data = data if isinstance(data, list) else []

        Phone = self.env["quo.phone.number"].sudo()
        seen_ids = set()

        for pn in data:
            if not isinstance(pn, dict):
                continue
            quo_id = (pn.get("id") or "").strip()  # PNxxxx
            if not quo_id:
                continue

            seen_ids.add(quo_id)

            vals = {
                "name": (pn.get("name") or "").strip() or False,
                "formatted_number": (pn.get("formattedNumber") or pn.get("formatted_number") or "").strip() or False,
                "raw_number": (pn.get("number") or "").strip() or False,
                "active": True,
            }

            rec = Phone.search([("quo_id", "=", quo_id)], limit=1)
            if rec:
                rec.write(vals)
            else:
                vals["quo_id"] = quo_id
                Phone.create(vals)

        # Optional: mark numbers not returned anymore as inactive
        if seen_ids:
            Phone.search([("quo_id", "not in", list(seen_ids)), ("active", "=", True)]).write({"active": False})

        return True


    # ---------- Utilities ----------
    @api.model
    def _parse_dt(self, value):
        """Parse ISO date to Odoo Datetime (naive UTC)."""
        if not value:
            return False
        # Common cases: 2024-01-01T12:34:56.789Z
        try:
            v = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(v)
            return fields.Datetime.to_string(dt.replace(tzinfo=None))
        except Exception:
            return False

    @api.model
    def _get_settings(self):
        ICP = self.env["ir.config_parameter"].sudo()
        return {
            "api_key": ICP.get_param("quo_transcripts.api_key") or "",
            "webhook_secret": ICP.get_param("quo_transcripts.webhook_secret") or "",
            "base_url": ICP.get_param("quo_transcripts.api_base_url") or "https://api.openphone.com/v1",
        }

    @api.model
    def _quo_request(self, method, path, params=None, json_payload=None):
        settings = self._get_settings()
        api_key = settings["api_key"]
        if not api_key:
            raise UserError(_("Missing Quo API Key. Set it in Settings → Quo Call Transcripts."))

        url = settings["base_url"].rstrip("/") + "/" + path.lstrip("/")
        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            resp = requests.request(
                method,
                url,
                headers=headers,
                params=params or None,
                json=json_payload if json_payload is not None else None,
                timeout=30,
            )
        except Exception as e:
            raise UserError(_("Quo API request failed: %s") % e)

        if resp.status_code >= 400:
            raise UserError(_("Quo API error %s: %s") % (resp.status_code, resp.text))

        # Some endpoints may return empty bodies; guard
        try:
            return resp.json()
        except Exception:
            return {}

    def _quo_get(self, path, params=None):
        return self._quo_request("GET", path, params=params)

    def _quo_post(self, path, payload):
        settings = self._get_settings()
        api_key = settings["api_key"]
        if not api_key:
            raise UserError(_("Missing Quo API Key. Set it in Settings → Quo Call Transcripts."))

        url = settings["base_url"].rstrip("/") + "/" + path.lstrip("/")

        headers = {
            "Authorization": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        _logger.info("QUO POST → %s", url)
        _logger.info("QUO POST PAYLOAD → %s", json.dumps(payload, indent=2))

        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        except Exception as e:
            _logger.exception("QUO POST NETWORK ERROR: %s", e)
            raise

        _logger.info("QUO RESPONSE STATUS → %s", resp.status_code)
        _logger.info("QUO RESPONSE HEADERS → %s", dict(resp.headers))
        _logger.info("QUO RESPONSE BODY → %s", resp.text)

        if resp.status_code >= 400:
            raise UserError(
                _("Quo API POST error %s:\n%s") % (resp.status_code, resp.text)
            )

        try:
            return resp.json()
        except Exception:
            _logger.warning("QUO RESPONSE NOT JSON — returning raw text")
            return resp.text

    @api.model
    def _find_partners_by_phone(self, numbers):
        numbers = [n for n in (numbers or []) if n]
        if not numbers:
            return self.env["res.partner"]

        patterns = set()

        for n in numbers:
            d = re.sub(r"\D+", "", n or "")
            if not d:
                continue

            # Use last 10 digits for NANP (US/CA), last 7 as fallback
            last10 = d[-10:] if len(d) >= 10 else d
            last7 = d[-7:] if len(d) >= 7 else ""

            # Build patterns that survive formatting: 800-555-0100 => %800%555%0100%
            if len(last10) == 10:
                patterns.add(f"%{last10[0:3]}%{last10[3:6]}%{last10[6:10]}%")  # %800%555%0100%
                patterns.add(f"%{last10[3:6]}%{last10[6:10]}%")                # %555%0100%
            if last7:
                patterns.add(f"%{last7[0:3]}%{last7[3:7]}%")                    # %555%0100%

            # Also keep raw digits as a sometimes-useful direct match
            patterns.add(last10)
            if last7:
                patterns.add(last7)

        if not patterns:
            return self.env["res.partner"]

        # OR domain across all patterns for phone/mobile
        domain = []
        first = True
        for p in patterns:
            chunk = ["|", ("phone", "ilike", p), ("mobile", "ilike", p)]
            if first:
                domain = chunk
                first = False
            else:
                domain = ["|"] + chunk + domain

        candidates = self.env["res.partner"].sudo().search(domain)

        # FINAL FILTER: sanitize candidate phone/mobile and compare by last 10/last 7 digits
        def norm_digits(val):
            return re.sub(r"\D+", "", val or "")

        wanted = set()
        for n in numbers:
            d = norm_digits(n)
            if len(d) >= 10:
                wanted.add(d[-10:])
            if len(d) >= 7:
                wanted.add(d[-7:])

        def is_match(p):
            pd = norm_digits(p.phone) + " " + norm_digits(p.mobile)
            # check last10/last7 existence anywhere in pd
            for w in wanted:
                if w and w in pd:
                    return True
            return False

        return candidates.filtered(is_match)

    def _format_bullets(self, items):
        """items: list[str] -> '• ...' lines"""
        if not items:
            return ""
        return "\n".join([f"• {str(x).strip()}" for x in items if str(x).strip()])

    def upsert_summary_from_payload(self, call_id, call_payload):
        MIN_DURATION_SECONDS = 10

        call_payload = call_payload or {}

        Call = self.sudo()
        call = Call.search([("quo_call_id", "=", call_id)], limit=1)
        if not call:
            _logger.info("Skipping QUO summary for call %s: no call record exists (possibly discarded short call).", call_id)
            return self.env["quo.call"]

        # If duration is already known and it's short, delete & skip
        if call.duration_seconds and call.duration_seconds < MIN_DURATION_SECONDS:
            _logger.info("Discarding QUO call %s on summary (duration=%ss < %ss)", call_id, call.duration_seconds, MIN_DURATION_SECONDS)
            call.unlink()
            return self.env["quo.call"]

        cs = call_payload.get("callSummary") or call_payload
        summary_list = cs.get("summary") or []
        next_steps_list = cs.get("nextSteps") or []

        vals = {
            "summary_text": self._format_bullets(summary_list),
            "next_steps_text": self._format_bullets(next_steps_list),
            "raw_summary_json": json.dumps(cs, ensure_ascii=False),
        }
        call.write(vals)

        call._post_potentially_related_to_documents()
        return call



    @api.model
    def upsert_recording_from_payload(self, call_id, call_payload):
        call_payload = call_payload or {}

        call = self.sudo().upsert_call_from_payload(call_id, call_payload)
        if not call:
            return call  # discarded

        media = (call_payload or {}).get("media") or []
        m0 = media[0] if media else {}

        vals = {
            "recording_url": m0.get("url") or False,
            "recording_mimetype": m0.get("type") or False,
            "recording_duration_seconds": int(m0.get("duration") or 0),
            "raw_recording_json": json.dumps(media, ensure_ascii=False),
        }

        call.write(vals)
        return call

    def _get_quo_author_partner(self):
        Partner = self.env["res.partner"].sudo()

        quo_partner = Partner.search([("name", "=", "QUO")], limit=1)
        if quo_partner:
            return quo_partner

        return Partner.create({
            "name": "QUO",
            "company_type": "company",
            "is_company": True,
        })

    @api.model
    def _get_or_create_partner_for_phone(self, phone, default_name=None):
        """Return a single res.partner for a phone.
        If none exists, create a contact named 'Unknown: <phone>' (or default_name if provided).
        """
        sanitized = self._sanitize_phone(phone)
        if not sanitized:
            return self.env["res.partner"]

        matches = self._find_partners_by_phone([sanitized])
        if matches:
            # choose the first deterministically
            return matches.sorted(lambda p: p.id)[0]

        # create a new contact — use the phone number in the name so records are
        # identifiable at a glance even before a name is manually added.
        name = default_name or f"Unknown: {sanitized}"
        return self.env["res.partner"].sudo().create({
            "name": name,
            "phone": sanitized,
        })

    # -------------------------------------------------------------------------
    # Two-way contact sync (Quo <-> Odoo)
    # -------------------------------------------------------------------------

    def _phone_key(self, phone):
        d = re.sub(r"\D+", "", phone or "")
        if not d:
            return ""
        return d[-10:] if len(d) > 10 else d

    def _quo_iter_contacts(self, max_pages=500, page_size=50):
        """Yield Quo contacts by paging GET /contacts."""
        page_token = None
        for _ in range(int(max_pages or 500)):
            payload = self._quo_get("contacts", params={"maxResults": min(int(page_size or 50), 50), **({"pageToken": page_token} if page_token else {})})
            for c in (payload.get("data") or []):
                yield c
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

    def _quo_contact_extract(self, quo_contact):
        """Extract (name, email, company, role, phones[]) from a Quo contact dict."""
        df = (quo_contact.get("defaultFields") or {})
        first = (df.get("firstName") or "").strip()
        last = (df.get("lastName") or "").strip()
        company = (df.get("company") or "").strip()
        role = (df.get("role") or "").strip()

        email = ""
        for e in (df.get("emails") or []):
            val = (e.get("value") or "").strip()
            if val:
                email = val
                break

        phones = []
        for p in (df.get("phoneNumbers") or []):
            val = (p.get("value") or "").strip()
            if val:
                phones.append(val)

        display_name = (f"{first} {last}").strip()
        if not display_name:
            display_name = company or ""
        return display_name, email, company, role, phones

    def _ensure_company_partner(self, company_name):
        if not company_name:
            return False
        Partner = self.env["res.partner"].sudo()
        company = Partner.search([("is_company", "=", True), ("name", "=", company_name)], limit=1)
        if not company:
            company = Partner.create({"name": company_name, "is_company": True, "company_type": "company"})
        return company

    def _update_partner_from_quo_if_empty(self, partner, display_name, email, company, role, phone_for_record):
        """Update partner fields only if empty (except name if Unknown Caller)."""
        vals = {}

        # Name: only set if empty or placeholder (Unknown Caller / Unknown: <phone>)
        if display_name:
            existing = (partner.name or "").strip()
            is_placeholder = (
                not existing
                or existing == "Unknown Caller"
                or existing.startswith("Unknown: ")
            )
            if is_placeholder:
                vals["name"] = display_name

        # Email: only set if empty
        if email and not (partner.email or "").strip():
            vals["email"] = email

        # Role/function: only set if empty
        if role and not (partner.function or "").strip():
            vals["function"] = role

        # Company: only set if empty and we have company
        if company and not partner.is_company and not partner.parent_id:
            comp = self._ensure_company_partner(company)
            if comp:
                vals["parent_id"] = comp.id
                vals["company_type"] = "person"

        # Phone: ensure at least one phone field is set (but don't override)
        if phone_for_record:
            if not (partner.phone or "").strip() and not (partner.mobile or "").strip():
                vals["phone"] = phone_for_record

        if vals:
            partner.sudo().write(vals)
        return bool(vals)

    def _is_valid_quo_phone(self, phone_value):
        # Require + and 10-15 digits (E.164-ish)
        if not phone_value:
            return False
        digits = re.sub(r"\D+", "", phone_value)
        if not phone_value.startswith("+"):
            return False
        return 10 <= len(digits) <= 15


    def _partner_to_quo_payload(self, partner, phone_value):
        """Build POST /contacts payload from an Odoo partner.

        Quo validator appears to require defaultFields.firstName to exist,
        and phoneNumbers[].value should be E.164 (e.g. +12345678901).
        """
        partner = partner.sudo()

        # Ensure phone_value is a string
        phone_value = (phone_value or "").strip()

        # Basic classification
        name = (partner.name or "").strip()
        is_company = bool(getattr(partner, "is_company", False) or (getattr(partner, "company_type", "") == "company"))

        first = last = None  # IMPORTANT: send null when not applicable
        company = None

        if is_company:
            company = name or None
            # first/last stay as None
        else:
            # Person contact
            if name:
                parts = name.split()
                first = parts[0] if parts else None
                last = " ".join(parts[1:]) if len(parts) > 1 else None

            if partner.parent_id and (partner.parent_id.name or "").strip():
                company = partner.parent_id.name.strip()

        emails = []
        email_val = (partner.email or "").strip()
        if email_val:
            emails.append({"name": "work", "value": email_val})

        payload = {
            "defaultFields": {
                # These two keys are included ALWAYS; null for company contacts
                "firstName": first,
                "lastName": last,

                # company can be null if unknown
                "company": company,

                # role can be null if unknown
                "role": ((partner.function or "").strip() or None),

                # omit emails if empty list? you can include [] but safer to omit
                "phoneNumbers": [{"name": "main", "value": phone_value}],
            },
            "source": "public-api",
            "externalId": f"odoo-res-partner-{partner.id}",
        }

        if emails:
            payload["defaultFields"]["emails"] = emails

        # Remove keys with None to keep payload clean (BUT keep firstName/lastName explicitly)
        df = payload["defaultFields"]
        for k in ["company", "role"]:
            if df.get(k) is None:
                df.pop(k, None)

        return payload


    @api.model
    def cron_two_way_contact_sync(self, quo_max_pages=500, odoo_batch=500):
        """
        Phase 1 (Quo -> Odoo):
        - List all Quo contacts.
        - For each phone on each Quo contact:
            - If Odoo partner exists for phone: fill missing fields only.
            - Else: create partner in Odoo.

        Phase 2 (Odoo -> Quo):
        - Scan Odoo partners with phone/mobile.
        - For each valid phone not already present in Quo, create a new Quo contact.
        - Do NOT update existing Quo contacts.
        """
        Partner = self.env["res.partner"].sudo()

        # -------------------------
        # Phase 1: Quo -> Odoo
        # -------------------------
        quo_phone_keys = set()
        created_odoo = 0
        updated_odoo = 0

        for qc in self.sudo()._quo_iter_contacts(max_pages=quo_max_pages, page_size=50):
            display_name, email, company, role, phones = self._quo_contact_extract(qc)
            if not phones:
                continue

            for raw_phone in phones:
                sanitized = self._sanitize_phone(raw_phone)
                if not sanitized:
                    continue

                key = self._phone_key(sanitized)
                if key:
                    quo_phone_keys.add(key)

                matches = self._find_partners_by_phone([sanitized])
                if matches:
                    partner = matches.sorted(lambda p: p.id)[0]
                    if self._update_partner_from_quo_if_empty(
                        partner, display_name, email, company, role, sanitized
                    ):
                        updated_odoo += 1
                    continue

                vals = {
                    "name": display_name or f"Unknown: {sanitized}",
                    "phone": sanitized,
                }
                if email:
                    vals["email"] = email
                if role:
                    vals["function"] = role

                if company:
                    comp = self._ensure_company_partner(company)
                    if comp:
                        vals["parent_id"] = comp.id
                        vals["company_type"] = "person"

                Partner.create(vals)
                created_odoo += 1

        _logger.info(
            "Quo contact sync phase1 done: created_odoo=%s updated_odoo=%s quo_phones_indexed=%s",
            created_odoo, updated_odoo, len(quo_phone_keys)
        )

        # -------------------------
        # Phase 2: Odoo -> Quo
        # -------------------------
        created_quo = 0
        checked_odoo = 0
        skipped_invalid = 0
        skipped_existing = 0
        failed_quo = 0

        domain = [
            "|", ("phone", "!=", False), ("mobile", "!=", False),
            ("active", "=", True),
        ]

        # Stable ordering so repeated cron runs are predictable
        partners = Partner.search(domain, limit=int(odoo_batch or 500), order="id asc")

        for partner in partners:
            # Try both numbers, not just one
            raw_numbers = [partner.phone, partner.mobile]
            seen_this_partner = set()

            for raw_phone in raw_numbers:
                phone_value = self._sanitize_phone(raw_phone)
                if not phone_value:
                    continue

                key = self._phone_key(phone_value)
                if not key or key in seen_this_partner:
                    continue
                seen_this_partner.add(key)

                if not self._is_valid_quo_phone(phone_value):
                    skipped_invalid += 1
                    _logger.info(
                        "Quo contact sync: skipping partner %s due to invalid phone for Quo: %s",
                        partner.id, phone_value
                    )
                    continue

                checked_odoo += 1

                if key in quo_phone_keys:
                    skipped_existing += 1
                    continue

                payload = self._partner_to_quo_payload(partner, phone_value)

                try:
                    resp = self._quo_post("contacts", payload)
                    created_quo += 1
                    quo_phone_keys.add(key)
                    _logger.info(
                        "Quo contact sync: created Quo contact for partner %s phone %s response=%s",
                        partner.id, phone_value, resp
                    )
                except Exception as e:
                    failed_quo += 1
                    _logger.warning(
                        "Quo contact sync: failed creating contact for partner %s (%s): %s",
                        partner.id, phone_value, e
                    )

        _logger.info(
            "Quo contact sync phase2 done: checked_odoo=%s created_quo=%s skipped_invalid=%s skipped_existing=%s failed_quo=%s",
            checked_odoo, created_quo, skipped_invalid, skipped_existing, failed_quo
        )

        return {
            "created_odoo": created_odoo,
            "updated_odoo": updated_odoo,
            "created_quo": created_quo,
            "checked_odoo": checked_odoo,
            "skipped_invalid": skipped_invalid,
            "skipped_existing": skipped_existing,
            "failed_quo": failed_quo,
            "quo_indexed": len(quo_phone_keys),
        }
        
    def _get_internal_partner_ids(self):
        return set(self.env["res.users"].sudo().search([("share", "=", False)]).mapped("partner_id").ids)

    def _mention_html(self, partner):
        # renders as a mention + clickable link in chatter
        return f'<a href="#" data-oe-model="res.partner" data-oe-id="{partner.id}">@{partner.display_name}</a>'

    def _format_call_time(self):
        self.ensure_one()
        dt = self.started_at or self.create_date
        if not dt:
            return ""
        # choose a sensible timezone: company tz > user tz > UTC
        tz = self.env.company.partner_id.tz or self.env.user.tz or "UTC"
        dt_local = fields.Datetime.context_timestamp(self.with_context(tz=tz), dt)
        return dt_local.strftime("%-I:%M %p")  # e.g. 2:36 PM (Linux). If Windows, use %#I.

    # ---------- Upserts from webhook / API ----------
    @api.model
    def upsert_call_from_payload(self, call_id, payload):
        """
        Create/update quo.call with best-effort parsing.

        Spam protection:
        - If we can determine duration and it is < 10 seconds, we discard the call:
          - If a record already exists, delete it.
          - If none exists, do not create anything.
        """
        MIN_DURATION_SECONDS = 10

        Call = self.sudo()
        rec = Call.search([("quo_call_id", "=", call_id)], limit=1)

        payload = payload or {}

        # Try extract common fields
        phone_number_id = payload.get("phoneNumberId") or payload.get("phone_number_id")
        direction = self._normalize_direction(payload.get("direction"))
        created_at = payload.get("createdAt") or payload.get("created_at")

        # completedAt is the one QUO sends on real calls; keep a couple fallbacks
        ended_at = (
            payload.get("completedAt")
            or payload.get("completed_at")
            or payload.get("endedAt")
            or payload.get("ended_at")
        )

        # Duration may appear in different places depending on event type
        duration = (
            payload.get("duration")
            or payload.get("durationSeconds")
            or payload.get("duration_seconds")
        )
        if not duration:
            media = payload.get("media") or []
            if media and isinstance(media, list) and isinstance(media[0], dict):
                duration = media[0].get("duration")

        # Spam protection: discard calls < 10 seconds if duration is known
        try:
            if duration not in (None, "", False):
                dur_int = int(float(duration))
                if dur_int < MIN_DURATION_SECONDS:
                    _logger.info("Discarding QUO call %s (duration=%ss < %ss)", call_id, dur_int, MIN_DURATION_SECONDS)
                    if rec:
                        rec.unlink()
                    return self.env["quo.call"]  # empty recordset
        except Exception:
            # If duration can't be parsed, do not block creation; just proceed.
            pass

        from_num = payload.get("from") or payload.get("fromNumber") or payload.get("from_phone") or ""
        to_num = payload.get("to") or payload.get("toNumber") or payload.get("to_phone") or ""

        # Ensure deterministic caller partners when phone numbers exist
        p_from = self.env["res.partner"]
        p_to = self.env["res.partner"]
        if from_num:
            p_from = self._get_or_create_partner_for_phone(from_num)
        if to_num:
            p_to = self._get_or_create_partner_for_phone(to_num)

        from_s = self._sanitize_phone(from_num)
        to_s = self._sanitize_phone(to_num)
        matched_partners = self._find_partners_by_phone([from_s, to_s])

        _logger.info(
            "Quo call partner match: from=%s to=%s matched_partner_ids=%s",
            from_num, to_num, matched_partners.ids,
        )

        participants = payload.get("participants")
        contact_ids = payload.get("contactIds") or payload.get("contact_ids")

        vals = {
            "quo_call_id": call_id,
            "phone_number_id": phone_number_id,
            "direction": direction,
            "started_at": self._parse_dt(created_at),
            "ended_at": self._parse_dt(ended_at),
            "duration_seconds": int(float(duration)) if duration not in (None, "", False) else 0,
            "from_number": from_num or False,
            "to_number": to_num or False,
            "caller_from_partner_id": p_from.id or False,
            "caller_to_partner_id": p_to.id or False,
            "from_sanitized": from_s,
            "to_sanitized": to_s,
            "partner_ids": [(6, 0, matched_partners.ids)],
            "participants_json": json.dumps(participants, ensure_ascii=False) if participants is not None else rec.participants_json,
            "contact_ids_json": json.dumps(contact_ids, ensure_ascii=False) if contact_ids is not None else rec.contact_ids_json,
            "raw_call_json": json.dumps(payload, ensure_ascii=False),
        }

        if rec:
            update_vals = {}

            # Never lose the raw payload
            update_vals["raw_call_json"] = vals["raw_call_json"]

            # Only write "direction" if meaningful, OR if we don't already have one
            if direction != "unknown" or rec.direction in (False, "unknown"):
                update_vals["direction"] = direction

            # Fill in other fields only when provided (avoid overwriting good data with blanks)
            for k in (
                "phone_number_id",
                "started_at",
                "ended_at",
                "duration_seconds",
                "from_number",
                "to_number",
                "caller_from_partner_id",
                "caller_to_partner_id",
                "from_sanitized",
                "to_sanitized",
                "partner_ids",
                "participants_json",
                "contact_ids_json",
            ):
                v = vals.get(k)
                if v not in (None, False, "", 0):
                    update_vals[k] = v

            rec.write(update_vals)
            return rec

        return Call.create(vals)

    def _get_external_partners(self):
        self.ensure_one()
        partners = self.partner_ids

        # internal user partner = res.users with share=False (not portal) whose partner_id matches
        internal_partner_ids = set(
            self.env["res.users"].sudo().search([("share", "=", False)]).mapped("partner_id").ids
        )
        return partners.filtered(lambda p: p.id not in internal_partner_ids)

    def _build_call_link_html(self):
        self.ensure_one()
        # direct backend link to the call form
        return '/web#id=%s&model=quo.call&view_type=form' % self.id

    def _ensure_caller_partners(self):
        for call in self:
            updates = {}
            if call.from_number and not call.caller_from_partner_id:
                p_from = call.sudo()._get_or_create_partner_for_phone(call.from_number)
                updates["caller_from_partner_id"] = p_from.id or False
            if call.to_number and not call.caller_to_partner_id:
                p_to = call.sudo()._get_or_create_partner_for_phone(call.to_number)
                updates["caller_to_partner_id"] = p_to.id or False
            if updates:
                call.sudo().with_context(skip_ensure_callers=True).write(updates)

    def _post_potentially_related_to_documents(self):
        for call in self:
            # We need a timestamp to compare against document creation
            call_dt = call.started_at or call.create_date
            if not call_dt:
                continue

            external_partners = call._get_external_partners()
            if not external_partners:
                continue

            # Body
            quo_author = call._get_quo_author_partner()
            internal_partner_ids = call._get_internal_partner_ids()

            # resolve “from/to” partners (create Unknown Caller if missing)
            p_from = call._get_or_create_partner_for_phone(call.from_number)
            p_to = call._get_or_create_partner_for_phone(call.to_number)

            # Prefer just the contact name (no "Company, Name" prefix)
            def _partner_short_title(p):
                return (p.name or p.display_name) if p else ""

            def _partner_clickable(p):
                if not p:
                    return ""
                return p._get_html_link(title=_partner_short_title(p))

            # Clickable link to the quo.call record (Odoo-generated HTML anchor)
            call_link = call._get_html_link(title="View full call details")

            # --- Follow-up activities (mail.activity) helpers ---
            def _extract_next_steps(call):
                steps = []
                try:
                    cs = json.loads(call.raw_summary_json or "{}")
                    steps = cs.get("nextSteps") or []
                except Exception:
                    steps = []

                if not steps and call.next_steps_text:
                    steps = [x.strip("• ").strip() for x in (call.next_steps_text or "").splitlines() if x.strip()]

                return [s.strip() for s in steps if isinstance(s, str) and s.strip()]

            todo_type = self.env.ref("mail.mail_activity_data_todo")
            next_steps = _extract_next_steps(call)

            def _activity_already_exists(model_name, res_id, step_text):
                return bool(self.env["mail.activity"].sudo().search_count([
                    ("res_model", "=", model_name),
                    ("res_id", "=", res_id),
                    ("activity_type_id", "=", todo_type.id),
                    ("summary", "=", step_text),
                ]))

            def _schedule_followups_on_record(rec, steps, call_link):
                """Create TODO activities for each next-step on exactly one record.
                Idempotent per record + summary text.
                """
                if not rec or not steps:
                    return

                user = getattr(rec, "user_id", False) or self.env.user
                due_date = fields.Date.context_today(self)

                for step in steps:
                    if _activity_already_exists(rec._name, rec.id, step):
                        continue

                    rec.sudo().activity_schedule(
                        "mail.mail_activity_data_todo",
                        summary=step,
                        user_id=user.id,
                        date_deadline=due_date,
                        note=(
                            "Created from QUO call summary.\n"
                            f"{call_link}"
                        ),
                    )

            def _is_newer(a, b):
                """Return True if record a is newer than record b (by create_date then id)."""
                if not a:
                    return False
                if not b:
                    return True
                ad = getattr(a, "create_date", False) or False
                bd = getattr(b, "create_date", False) or False
                if ad and bd and ad != bd:
                    return ad > bd
                return (a.id or 0) > (b.id or 0)

            # We'll collect the single best target for activities across ALL external partners,
            # to guarantee activities are created only once per call.
            best_opp = self.env["crm.lead"]
            best_quote = self.env["sale.order"]
            best_ticket = self.env["helpdesk.ticket"]

            time_str = call._format_call_time() or ""

            name_1_html = _partner_clickable(p_from)
            name_2_html = _partner_clickable(p_to)
            between_html = " and ".join([x for x in [name_1_html, name_2_html] if x]) or "unknown participants"

            # internal participants to ping (if either side is internal)
            to_ping = self.env["res.partner"]
            for p in (p_from | p_to):
                if p and p.id in internal_partner_ids:
                    to_ping |= p

            def nl2br(txt):
                if not txt:
                    return Markup("")
                return Markup("<br/>").join(escape(txt).splitlines())

            parts = []

            parts.append(
                Markup("<p><b>Potentially related call</b> at <b>")
                + escape(time_str)
                + Markup("</b> between <b>")
                + Markup(between_html)
                + Markup("</b>.</p>")
            )

            parts.append(Markup("<br/>"))

            if call.summary_text:
                parts.append(Markup("<b>Summary:</b><br/>") + nl2br(call.summary_text))
                parts.append(Markup("<br/><br/>"))

            if call.next_steps_text:
                parts.append(Markup("<b>Action items:</b><br/>") + nl2br(call.next_steps_text))
                parts.append(Markup("<br/><br/>"))

            if to_ping:
                notified_txt = ", ".join([f"@{p.display_name}" for p in to_ping])
                parts.append(Markup("<b>Notified:</b> ") + escape(notified_txt))
                parts.append(Markup("<br/><br/>"))

            parts.append(Markup(call_link))
            body_html = Markup("").join(parts)

            for partner in external_partners:
                # -------------------------
                # Opportunities (CRM)
                # -------------------------
                opp_domain = [
                    ("type", "=", "opportunity"),
                    ("active", "=", True),
                    ("stage_id.is_won", "=", False),
                    ("probability", ">", 0),
                ]
                if call_dt:
                    opp_domain.append(("create_date", "<", call_dt))
                opp_domain += [
                    "|",
                        ("partner_id", "child_of", partner.commercial_partner_id.id),
                        ("message_partner_ids", "in", partner.ids),
                ]
                opportunities = self.env["crm.lead"].sudo().search(opp_domain, order="create_date desc, id desc")

                if opportunities:
                    _logger.info(
                        "Posting Quo call %s to %d opportunities for partner %s: %s",
                        call.id, len(opportunities), partner.display_name, opportunities.ids
                    )
                    if _is_newer(opportunities[0], best_opp[0] if best_opp else False):
                        best_opp = opportunities[0:1]

                # -------------------------
                # Quotes (Sales)
                # -------------------------
                quote_domain = [("state", "in", ["draft", "sent"])]
                if call_dt:
                    quote_domain.append(("create_date", "<", call_dt))
                quote_domain += [
                    "|", "|", "|",
                        ("partner_id", "child_of", partner.commercial_partner_id.id),
                        ("partner_shipping_id", "child_of", partner.commercial_partner_id.id),
                        ("partner_invoice_id", "child_of", partner.commercial_partner_id.id),
                        ("message_partner_ids", "in", partner.ids),
                ]
                quotes = self.env["sale.order"].sudo().search(quote_domain, order="create_date desc, id desc")

                if quotes:
                    _logger.info(
                        "Posting Quo call %s to %d quotes for partner %s: %s",
                        call.id, len(quotes), partner.display_name, quotes.ids
                    )
                    if _is_newer(quotes[0], best_quote[0] if best_quote else False):
                        best_quote = quotes[0:1]

                ticket_domain = [
                    ("active", "=", True),
                ]
                if call_dt:
                    ticket_domain.append(("create_date", "<", call_dt))
                ticket_domain += [
                    "|",
                        ("partner_id", "child_of", partner.commercial_partner_id.id),
                        ("message_partner_ids", "in", partner.ids),
                ]
                tickets = self.env["helpdesk.ticket"].sudo().search(
                    ticket_domain,
                    order="create_date desc, id desc"
                )

                if tickets:
                    _logger.info(
                        "Posting Quo call %s to %d helpdesk tickets for partner %s: %s",
                        call.id, len(tickets), partner.display_name, tickets.ids
                    )
                    if _is_newer(tickets[0], best_ticket[0] if best_ticket else False):
                        best_ticket = tickets[0:1]

                # Post to opportunities
                for rec in opportunities:
                    rec.message_post(
                        body=body_html,
                        body_is_html=True,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                        author_id=quo_author.id,
                        partner_ids=[(6, 0, to_ping.ids)] if to_ping else False,
                    )

                # Post to quotes
                for rec in quotes:
                    rec.message_post(
                        body=body_html,
                        body_is_html=True,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                        author_id=quo_author.id,
                        partner_ids=[(6, 0, to_ping.ids)] if to_ping else False,
                    )

                for rec in tickets:
                    rec.message_post(
                        body=body_html,
                        body_is_html=True,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                        author_id=quo_author.id,
                        partner_ids=[(6, 0, to_ping.ids)] if to_ping else False,
                    )

                # Post to the partner record as well (always, for external partners)
                partner.message_post(
                    body=body_html,
                    body_is_html=True,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                    author_id=quo_author.id,
                    partner_ids=[(6, 0, to_ping.ids)] if to_ping else False,
                )

            # Create follow-up activities ONLY on the latest opportunity.
            # If no opportunity exists, create one and assign it to Derek deBlois.
            if next_steps:
                if best_opp:
                    activity_target = best_opp[0]
                elif external_partners:
                    # Resolve Derek deBlois as the assignee
                    derek_user = self.env["res.users"].sudo().search([
                        "|",
                        ("login", "=", "derek@r-e-a-l.it"),
                        ("email", "=", "derek@r-e-a-l.it"),
                    ], limit=1)
                    if not derek_user:
                        derek_user = self.env["res.users"].sudo().search([
                            ("name", "ilike", "Derek deBlois"),
                        ], limit=1)

                    fallback_partner = external_partners[0]
                    activity_target = self.env["crm.lead"].sudo().create({
                        "name": f"Follow-up: {fallback_partner.display_name}",
                        "type": "opportunity",
                        "partner_id": fallback_partner.id,
                        "user_id": (derek_user.id if derek_user else self.env.user.id),
                    })
                    _logger.info(
                        "Quo call %s: created opportunity %s for partner %s (assigned to %s)",
                        call.id, activity_target.id,
                        fallback_partner.display_name,
                        derek_user.name if derek_user else "current user",
                    )
                else:
                    activity_target = None

                if activity_target:
                    _schedule_followups_on_record(activity_target, next_steps, call_link)

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        if not self.env.context.get("skip_ensure_callers"):
            records._ensure_caller_partners()
        return records

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_ensure_callers"):
            self._ensure_caller_partners()
        return res


class QuoCallTranscript(models.Model):
    _name = "quo.call.transcript"
    _description = "Quo Call Transcript"
    _order = "created_at desc, id desc"

    call_id = fields.Many2one("quo.call", required=True, ondelete="cascade", index=True)
    quo_call_id = fields.Char(related="call_id.quo_call_id", store=True, index=True)

    status = fields.Char(string="Status", index=True)
    created_at = fields.Datetime(string="Created At", index=True)
    duration_seconds = fields.Integer(string="Duration (s)")

    raw_transcript_json = fields.Text(string="Raw Transcript (JSON)")
    line_ids = fields.One2many("quo.call.transcript.line", "transcript_id", string="Dialogue")

    _sql_constraints = [
        ("one_transcript_per_call", "unique(call_id)", "Only one transcript per call is stored."),
    ]

    @api.model
    def upsert_from_transcript_payload(self, call_id, transcript_payload):
        """
        transcript_payload shape (best-effort):
          {
            "callId": "...",
            "createdAt": "...",
            "duration": 123,
            "status": "...",
            "dialogue": [{...}, ...]
          }

        Spam protection:
        - If transcript duration < 10s, do not create call/transcript at all.
        """
        MIN_DURATION_SECONDS = 10

        transcript_payload = transcript_payload or {}

        # duration is present on transcript payload
        duration = (
            transcript_payload.get("duration")
            or transcript_payload.get("durationSeconds")
            or transcript_payload.get("duration_seconds")
        )
        try:
            if duration not in (None, "", False) and int(float(duration)) < MIN_DURATION_SECONDS:
                _logger.info("Discarding QUO transcript for call %s (duration=%ss < %ss)", call_id, int(float(duration)), MIN_DURATION_SECONDS)
                # If a call record already exists, remove it too (keeps DB clean)
                existing_call = self.env["quo.call"].sudo().search([("quo_call_id", "=", call_id)], limit=1)
                if existing_call:
                    existing_call.unlink()
                return False
        except Exception:
            pass

        Call = self.env["quo.call"].sudo()
        Transcript = self.sudo()
        Line = self.env["quo.call.transcript.line"].sudo()

        call = Call.search([("quo_call_id", "=", call_id)], limit=1)
        if not call:
            call = Call.create({"quo_call_id": call_id, "direction": "unknown"})

        rec = Transcript.search([("call_id", "=", call.id)], limit=1)

        created_at = transcript_payload.get("createdAt") or transcript_payload.get("created_at")
        status = transcript_payload.get("status") or ""

        vals = {
            "call_id": call.id,
            "status": status,
            "created_at": self.env["quo.call"]._parse_dt(created_at),
            "duration_seconds": int(float(duration)) if duration not in (None, "", False) else 0,
            "raw_transcript_json": json.dumps(transcript_payload, ensure_ascii=False),
        }

        if rec:
            rec.write(vals)
            rec.line_ids.unlink()
            transcript = rec
        else:
            transcript = Transcript.create(vals)

        dialogue = transcript_payload.get("dialogue") or []
        seq = 1
        line_vals = []
        for item in dialogue:
            identifier = item.get("identifier") or ""
            partner = self.env["quo.call"].sudo()._get_or_create_partner_for_phone(identifier)

            line_vals.append({
                "transcript_id": transcript.id,
                "sequence": seq,
                "start_ms": int(item.get("start") or item.get("startMs") or 0),
                "end_ms": int(item.get("end") or item.get("endMs") or 0),
                "content": item.get("content") or "",
                "identifier": identifier,
                "user_id": item.get("userId") or item.get("user_id") or "",
                "speaker_label": identifier or (item.get("userId") or ""),
                "partner_id": partner.id or False,
            })
            seq += 1

        if line_vals:
            Line.create(line_vals)

        return transcript


class QuoCallTranscriptLine(models.Model):
    _name = "quo.call.transcript.line"
    _description = "Quo Call Transcript Line"
    _order = "sequence asc, id asc"

    transcript_id = fields.Many2one("quo.call.transcript", required=True, ondelete="cascade", index=True)
    sequence = fields.Integer(default=1, index=True)

    start_ms = fields.Integer(string="Start (ms)")
    end_ms = fields.Integer(string="End (ms)")
    content = fields.Text(string="Content")

    identifier = fields.Char(string="Identifier")
    user_id = fields.Char(string="User ID")
    speaker_label = fields.Char(string="Speaker")

    partner_id = fields.Many2one("res.partner", string="Partner", index=True)

class QuoText(models.Model):
    _name = "quo.text"
    _description = "Quo Text Message"
    _inherit = ["mail.thread"]
    _order = "created_at desc, id desc"

    name = fields.Char(string="Display Name", compute="_compute_name", store=True)

    quo_message_id = fields.Char(string="Quo Message ID", required=True, index=True)
    phone_number_id = fields.Char(string="Phone Number ID", index=True)
    conversation_id = fields.Char(string="Conversation ID", index=True)

    direction = fields.Selection(
        [("inbound", "Inbound"), ("outbound", "Outbound"), ("unknown", "Unknown")],
        default="unknown",
        string="Direction",
        index=True,
    )

    created_at = fields.Datetime(string="Created At", index=True)
    status = fields.Char(string="Status", index=True)

    from_number = fields.Char(string="From")
    to_number = fields.Char(string="To")
    from_sanitized = fields.Char(string="From (sanitized)", index=True)
    to_sanitized = fields.Char(string="To (sanitized)", index=True)

    from_partner_id = fields.Many2one("res.partner", string="From Partner", index=True, ondelete="set null")
    to_partner_id = fields.Many2one("res.partner", string="To Partner", index=True, ondelete="set null")

    body = fields.Text(string="Message")
    media_json = fields.Text(string="Media (JSON)")
    raw_message_json = fields.Text(string="Raw Message (JSON)")

    _sql_constraints = [
        ("quo_message_id_unique", "unique(quo_message_id)", "Quo Message ID must be unique."),
    ]

    @api.depends("direction", "from_partner_id", "to_partner_id", "from_number", "to_number", "created_at")
    def _compute_name(self):
        for rec in self:
            dir_label = "Text"
            if rec.direction == "inbound":
                dir_label = "Inbound text"
            elif rec.direction == "outbound":
                dir_label = "Outbound text"

            def _label(p, num):
                if p and p.name:
                    return p.name
                return num or ""

            left = _label(rec.from_partner_id, rec.from_number)
            right = _label(rec.to_partner_id, rec.to_number)
            rec.name = f"{dir_label} from {left} to {right}".strip()

    def _get_internal_partner_ids(self):
        return set(self.env["res.users"].sudo().search([("share", "=", False)]).mapped("partner_id").ids)

    def _get_external_partners_from_message(self):
        """Return external partners involved in this message (exclude internal user partners)."""
        self.ensure_one()
        internal_partner_ids = self._get_internal_partner_ids()
        partners = (self.from_partner_id | self.to_partner_id)
        return partners.filtered(lambda p: p and p.id not in internal_partner_ids)

    def _fetch_media_as_attachments(self, media_list):
        """Return (attachment_ids, fallback_links) for QUO media."""
        import os
        import mimetypes
        from urllib.parse import urlparse

        IrAttachment = self.env["ir.attachment"].sudo()

        def _guess_ext(ct, fallback=""):
            ct = (ct or "").split(";")[0].strip().lower()
            if ct:
                ext = mimetypes.guess_extension(ct) or ""
                if ext:
                    return ext
            ft = (fallback or "").split(";")[0].strip().lower()
            if ft:
                ext = mimetypes.guess_extension(ft) or ""
                if ext:
                    return ext
            return ".bin"

        def _filename(url, ct, mtype, idx):
            try:
                base = os.path.basename(urlparse(url).path or "") or ""
            except Exception:
                base = ""
            if not base or "." not in base:
                base = f"quo_media_{idx}{_guess_ext(ct, mtype)}"
            return base

        attachment_ids = []
        fallback_links = []

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Odoo)",
            "Accept": "*/*",
        }

        for idx, m in enumerate(media_list or [], start=1):
            url = (m or {}).get("url")
            mtype = (m or {}).get("type") or ""
            if not url:
                continue

            try:
                resp = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
                ct = (resp.headers.get("Content-Type") or mtype or "").strip()

                if not (resp.ok and resp.content):
                    fallback_links.append((ct or "file", url))
                    continue

                # Guard: don't save HTML error pages as "images"
                if (ct.lower().startswith("text/html") or resp.content[:20].lstrip().lower().startswith(b"<!doctype html")):
                    fallback_links.append((ct or "file", url))
                    continue

                fname = _filename(url, ct, mtype, idx)

                att = IrAttachment.create({
                    "name": fname,
                    "datas": base64.b64encode(resp.content).decode("ascii"),  # Binary field expects base64 string
                    "mimetype": (ct.split(";")[0].strip() if ct else False),
                })
                attachment_ids.append(att.id)

            except Exception:
                fallback_links.append((mtype or "file", url))

        return attachment_ids, fallback_links

    def _post_to_related_documents_and_contacts(self):
        """Log the text on:
        - BOTH involved contacts (always, as long as they are not internal user partners)
        - ALL matching open opportunities and draft/sent quotes for those external contacts
        - Attach any media as chatter attachments (images/files), not just links
        """
        import os
        import mimetypes
        from urllib.parse import urlparse

        def nl2br(txtval):
            if not txtval:
                return Markup("")
            return Markup("<br/>").join(escape(txtval).splitlines())

        def _partner_short_title(p):
            return (p.name or p.display_name) if p else ""

        def _partner_clickable(p):
            if not p:
                return ""
            return p._get_html_link(title=_partner_short_title(p))

        def _guess_ext(content_type, fallback=""):
            ct = (content_type or "").split(";")[0].strip().lower()
            if ct:
                ext = mimetypes.guess_extension(ct) or ""
                if ext:
                    return ext
            fb = (fallback or "").split(";")[0].strip().lower()
            if fb:
                ext = mimetypes.guess_extension(fb) or ""
                if ext:
                    return ext
            return ".bin"

        def _filename_from_url(url, content_type, fallback_type, idx):
            try:
                base = os.path.basename(urlparse(url).path or "") or ""
            except Exception:
                base = ""
            if not base or "." not in base:
                base = f"quo_media_{idx}{_guess_ext(content_type, fallback_type)}"
            return base

        for txt in self:
            msg_dt = txt.created_at or txt.create_date
            external_partners = txt._get_external_partners_from_message()

            from_html = _partner_clickable(txt.from_partner_id) or escape(txt.from_number or "")
            to_html = _partner_clickable(txt.to_partner_id) or escape(txt.to_number or "")

            # -------------------------
            # Build attachments payload for message_post (list of (name, b64data))
            # -------------------------
            media_list = []
            try:
                media_list = json.loads(txt.media_json or "[]") if txt.media_json else []
            except Exception:
                media_list = []

            attachments = []
            fallback_links = []

            headers = {
                "User-Agent": "Mozilla/5.0 (compatible; Odoo)",
                "Accept": "*/*",
            }

            for idx, m in enumerate(media_list or [], start=1):
                url = (m or {}).get("url")
                mtype = (m or {}).get("type") or ""
                if not url:
                    continue

                try:
                    resp = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
                    ct = (resp.headers.get("Content-Type") or mtype or "").strip()

                    if not (resp.ok and resp.content):
                        fallback_links.append((ct or mtype or "file", url))
                        continue

                    # Don't attach HTML error pages
                    head = resp.content[:64].lstrip().lower()
                    if (ct.lower().startswith("text/html") or head.startswith(b"<!doctype html") or head.startswith(b"<html")):
                        fallback_links.append((ct or mtype or "file", url))
                        continue

                    fname = _filename_from_url(url, ct, mtype, idx)

                    # IMPORTANT: message_post expects base64 content for attachments
                    attachments.append((fname, resp.content))

                except Exception:
                    _logger.exception("Failed fetching QUO media url=%s", url)
                    fallback_links.append((mtype or "file", url))

            _logger.info(
                "QUO text %s media: attachments=%d fallback_links=%d",
                txt.id, len(attachments), len(fallback_links)
            )

            # -------------------------
            # Build message body
            # -------------------------
            parts = []
            parts.append(
                Markup("<p><b>Text from </b>")
                + Markup(from_html)
                + Markup("<b> to </b>")
                + Markup(to_html)
                + Markup("</p>")
            )

            if txt.body:
                parts.append(Markup("<p>") + nl2br(txt.body) + Markup("</p>"))
            else:
                parts.append(Markup("<p><i>(No message body)</i></p>"))

            if fallback_links:
                parts.append(Markup("<p><b>Media (links):</b><br/>"))
                for label, url in fallback_links:
                    parts.append(
                        Markup(f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(label)}</a><br/>')
                    )
                parts.append(Markup("</p>"))

            body_html = Markup("").join(parts)

            quo_author = self.env["quo.call"].sudo()._get_quo_author_partner()

            # -------------------------
            # Post to contacts (always), for external contacts only
            # -------------------------
            for p in external_partners:
                p.message_post(
                    body=body_html,
                    body_is_html=True,
                    message_type="comment",
                    subtype_xmlid="mail.mt_note",
                    author_id=quo_author.id,
                    attachments=attachments or None,
                )

            # -------------------------
            # Post to opportunities and quotes for each external partner
            # -------------------------
            for partner in external_partners:
                opp_domain = [
                    ("type", "=", "opportunity"),
                    ("active", "=", True),
                    ("stage_id.is_won", "=", False),
                    ("probability", ">", 0),
                ]
                if msg_dt:
                    opp_domain.append(("create_date", "<", msg_dt))
                opp_domain += [
                    "|",
                        ("partner_id", "child_of", partner.commercial_partner_id.id),
                        ("message_partner_ids", "in", partner.ids),
                ]
                opportunities = self.env["crm.lead"].sudo().search(opp_domain, order="create_date desc, id desc")

                quote_domain = [
                    ("state", "in", ["draft", "sent"]),
                ]
                if msg_dt:
                    quote_domain.append(("create_date", "<", msg_dt))
                quote_domain += [
                    "|", "|", "|",
                        ("partner_id", "child_of", partner.commercial_partner_id.id),
                        ("partner_shipping_id", "child_of", partner.commercial_partner_id.id),
                        ("partner_invoice_id", "child_of", partner.commercial_partner_id.id),
                        ("message_partner_ids", "in", partner.ids),
                ]
                quotes = self.env["sale.order"].sudo().search(quote_domain, order="create_date desc, id desc")

                ticket_domain = [
                    ("active", "=", True),
                ]
                if msg_dt:
                    ticket_domain.append(("create_date", "<", msg_dt))
                ticket_domain += [
                    "|",
                        ("partner_id", "child_of", partner.commercial_partner_id.id),
                        ("message_partner_ids", "in", partner.ids),
                ]
                tickets = self.env["helpdesk.ticket"].sudo().search(
                    ticket_domain,
                    order="create_date desc, id desc"
                )

                for rec in opportunities:
                    rec.message_post(
                        body=body_html,
                        body_is_html=True,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                        author_id=quo_author.id,
                        attachments=attachments or None,
                    )

                for rec in quotes:
                    rec.message_post(
                        body=body_html,
                        body_is_html=True,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                        author_id=quo_author.id,
                        attachments=attachments or None,
                    )

                for rec in tickets:
                    rec.message_post(
                        body=body_html,
                        body_is_html=True,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                        author_id=quo_author.id,
                        attachments=attachments or None,
                    )


    @api.model
    def upsert_text_from_payload(self, message_id, payload):
        """Create/update quo.text from message.received/message.delivered event."""
        payload = payload or {}
        Text = self.sudo()
        rec = Text.search([("quo_message_id", "=", message_id)], limit=1)

        from_num = payload.get("from") or ""
        to_num = payload.get("to") or ""
        from_s = self.env["quo.call"].sudo()._sanitize_phone(from_num)
        to_s = self.env["quo.call"].sudo()._sanitize_phone(to_num)

        # Create / resolve partners (Unknown Caller if missing)
        p_from = self.env["quo.call"].sudo()._get_or_create_partner_for_phone(from_num) if from_num else self.env["res.partner"]
        p_to = self.env["quo.call"].sudo()._get_or_create_partner_for_phone(to_num) if to_num else self.env["res.partner"]

        direction = self.env["quo.call"].sudo()._normalize_direction(payload.get("direction"))

        created_at = payload.get("createdAt") or payload.get("created_at")
        dt_created = self.env["quo.call"].sudo()._parse_dt(created_at)

        body = (
            payload.get("body")
            or payload.get("content")
            or payload.get("text")
            or payload.get("message")
            or ""
        )

        media = payload.get("media") or []
        vals = {
            "quo_message_id": message_id,
            "phone_number_id": payload.get("phoneNumberId") or payload.get("phone_number_id"),
            "conversation_id": payload.get("conversationId") or payload.get("conversation_id"),
            "direction": direction,
            "created_at": dt_created,
            "status": payload.get("status") or "",
            "from_number": from_num or False,
            "to_number": to_num or False,
            "from_sanitized": from_s,
            "to_sanitized": to_s,
            "from_partner_id": p_from.id or False,
            "to_partner_id": p_to.id or False,
            "body": body,
            "media_json": json.dumps(media, ensure_ascii=False),
            "raw_message_json": json.dumps(payload, ensure_ascii=False),
        }

        created = False

        if rec:
            rec.write({k: v for k, v in vals.items() if v not in (None, False, "") or k in ("raw_message_json", "media_json")})
            txt = rec
        else:
            txt = Text.create(vals)
            created = True

        # Post chatter logs ONLY on first creation to avoid duplicates from webhook status updates
        if created:
            try:
                txt._post_to_related_documents_and_contacts()
            except Exception:
                _logger.exception("Failed to post QUO text %s to related documents/contacts", txt.id)

        return txt

        return txt
