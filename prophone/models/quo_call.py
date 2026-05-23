# -*- coding: utf-8 -*-

import re
import json
import logging
from datetime import datetime
from markupsafe import Markup, escape
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
    def _get_or_create_partner_for_phone(self, phone, default_name="Unknown Caller"):
        """Return a single res.partner for a phone. If none, create Unknown Caller."""
        sanitized = self._sanitize_phone(phone)
        if not sanitized:
            return self.env["res.partner"]

        matches = self._find_partners_by_phone([sanitized])
        if matches:
            # choose the first deterministically
            return matches.sorted(lambda p: p.id)[0]

        # create a new contact with that number
        return self.env["res.partner"].sudo().create({
            "name": default_name,
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

        # Name: only set if empty or Unknown Caller
        if display_name:
            if not (partner.name or "").strip() or (partner.name or "").strip() == "Unknown Caller":
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
                    "name": display_name or "Unknown Caller",
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
            p_from = self._get_or_create_partner_for_phone(from_num, default_name="Unknown Caller")
        if to_num:
            p_to = self._get_or_create_partner_for_phone(to_num, default_name="Unknown Caller")

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
                p_from = call.sudo()._get_or_create_partner_for_phone(call.from_number, default_name="Unknown Caller")
                updates["caller_from_partner_id"] = p_from.id or False
            if call.to_number and not call.caller_to_partner_id:
                p_to = call.sudo()._get_or_create_partner_for_phone(call.to_number, default_name="Unknown Caller")
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

            # Create follow-up activities with your rules (only once per call)
            # Priority: newest opportunity -> newest quote -> (fallback) first external partner
            if next_steps:
                if best_opp:
                    target = best_opp[0]
                elif best_quote:
                    target = best_quote[0]
                elif best_ticket:
                    target = best_ticket[0]
                else:
                    target = external_partners[0]

                _schedule_followups_on_record(target, next_steps, call_link)

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
