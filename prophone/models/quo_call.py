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

    name = fields.Char(string="Display Name", compute="_compute_name", store=True)

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

    @api.depends("direction", "from_number", "to_number", "caller_from_partner_id", "caller_to_partner_id")
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
    def _quo_get(self, path):
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
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code >= 400:
            raise UserError(_("Quo API error %s: %s") % (resp.status_code, resp.text))
        return resp.json()

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

        # Create it if missing
        image_b64 = None
        try:
            resp = requests.get(
                "https://media.licdn.com/dms/image/v2/D5622AQET2MqPqr5tRw/feedshare-shrink_800/B56ZpuetfHHkAg-/0/1762790136108"
            )
            if resp.ok:
                image_b64 = base64.b64encode(resp.content)
        except Exception:
            pass

        return Partner.create({
            "name": "QUO",
            "company_type": "company",
            "is_company": True,
            "email": "noreply@quo.ai",
            "image_1920": image_b64,
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

            call_url = call._build_call_link_html()

            for partner in external_partners:
                # -------------------------
                # Opportunities (CRM)
                # -------------------------
                # "open" opportunities: active, not won; also exclude lost if probability==0 and lost_reason set
                opp_domain = [
                    ("type", "=", "opportunity"),
                    ("active", "=", True),
                    ("stage_id.is_won", "=", False),
                    ("probability", ">", 0),
                    ("create_date", "<", call_dt),
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

                # -------------------------
                # Quotes (Sales)
                # -------------------------
                # "open" quotes: draft/sent only; exclude confirmed (sale), done, cancelled
                quote_domain = [
                    ("state", "in", ["draft", "sent"]),
                    ("create_date", "<", call_dt),
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

                def _activity_already_exists(model_name, res_id, step_text):
                    return bool(self.env["mail.activity"].sudo().search_count([
                        ("res_model", "=", model_name),
                        ("res_id", "=", res_id),
                        ("activity_type_id", "=", todo_type.id),
                        ("summary", "=", step_text),
                    ]))

                def _schedule_followups_on_record(rec, steps, call_link):
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

                todo_type = self.env.ref("mail.mail_activity_data_todo")
                next_steps = _extract_next_steps(call)

                # Create follow-up activities with your rules
                if next_steps:
                    target = False
                    if opportunities and quotes:
                        target = opportunities[0]  # only on most recent opportunity
                    elif opportunities:
                        target = opportunities[0]  # most recent opportunity
                    elif quotes:
                        target = quotes[0]         # most recent quote

                    if target:
                        _schedule_followups_on_record(target, next_steps, call_link)

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

    def _post_to_related_documents_and_contacts(self):
        """Log the text on:
        - BOTH involved contacts (always, as long as they are not internal user partners)
        - ALL matching open opportunities and draft/sent quotes for those external contacts
        - Attach any media as chatter attachments (images/files), not just links
        """
        import os
        import mimetypes
        from urllib.parse import urlparse

        for txt in self:
            msg_dt = txt.created_at or txt.create_date
            external_partners = txt._get_external_partners_from_message()

            # Always log on the contact chatter (for external contacts)

            def nl2br(txtval):
                if not txtval:
                    return Markup("")
                return Markup("<br/>").join(escape(txtval).splitlines())

            # Clickable partner names (short title)
            def _partner_short_title(p):
                return (p.name or p.display_name) if p else ""

            def _partner_clickable(p):
                if not p:
                    return ""
                return p._get_html_link(title=_partner_short_title(p))

            from_html = _partner_clickable(txt.from_partner_id) or escape(txt.from_number or "")
            to_html = _partner_clickable(txt.to_partner_id) or escape(txt.to_number or "")

            # -------------------------
            # Build attachments from media
            # -------------------------
            media_list = []
            try:
                media_list = json.loads(txt.media_json or "[]") if txt.media_json else []
            except Exception:
                media_list = []

            def _guess_extension(content_type, fallback_mtype=""):
                ct = (content_type or "").split(";")[0].strip().lower()
                if ct:
                    ext = mimetypes.guess_extension(ct) or ""
                    if ext:
                        return ext
                # fallback to provided mtype from payload
                ft = (fallback_mtype or "").split(";")[0].strip().lower()
                if ft:
                    ext = mimetypes.guess_extension(ft) or ""
                    if ext:
                        return ext
                return ".bin"

            def _guess_filename(url, content_type, mtype, idx):
                # Try to get a filename from the URL path
                try:
                    path = urlparse(url).path or ""
                    base = os.path.basename(path) or ""
                except Exception:
                    base = ""

                # If URL has no filename or no extension, generate one with a good extension
                if not base or "." not in base:
                    ext = _guess_extension(content_type, mtype)
                    base = f"quo_media_{idx}{ext}"

                return base

            def _looks_like_image_bytes(b):
                # Simple magic-byte checks for common image formats
                if not b or len(b) < 12:
                    return False
                if b.startswith(b"\xFF\xD8\xFF"):  # JPEG
                    return True
                if b.startswith(b"\x89PNG\r\n\x1a\n"):  # PNG
                    return True
                if b.startswith(b"GIF87a") or b.startswith(b"GIF89a"):  # GIF
                    return True
                if b[0:4] == b"RIFF" and b[8:12] == b"WEBP":  # WEBP
                    return True
                return False

            attachments = []
            fallback_links = []

            headers = {
                # Some CDNs return an HTML page or block without a UA
                "User-Agent": "Mozilla/5.0 (compatible; Odoo; +https://odoo.com)",
                "Accept": "*/*",
            }

            for idx, m in enumerate(media_list or [], start=1):
                url = (m or {}).get("url")
                mtype = (m or {}).get("type") or ""
                if not url:
                    continue

                try:
                    resp = requests.get(url, headers=headers, timeout=45, allow_redirects=True)
                    if not (resp.ok and resp.content):
                        fallback_links.append((mtype or "file", url))
                        continue

                    content_type = (resp.headers.get("Content-Type") or "").strip()
                    content = resp.content

                    # If server returned HTML (login/error page), don't attach it
                    if content_type.lower().startswith("text/html") or content[:20].lstrip().lower().startswith(b"<!doctype html"):
                        fallback_links.append((mtype or "file", url))
                        continue

                    filename = _guess_filename(url, content_type, mtype, idx)

                    # If it's supposed to be an image but doesn't look like one, fallback to link
                    if ("image/" in (content_type.lower() or mtype.lower())) and not _looks_like_image_bytes(content):
                        fallback_links.append((mtype or filename, url))
                        continue

                    # IMPORTANT: store as base64 *string* (ascii), not bytes
                    attachments.append((filename, base64.b64encode(content).decode("ascii")))

                except Exception:
                    fallback_links.append((mtype or "file", url))

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

            # If we couldn't fetch media to attach, show fallback links (rare)
            if fallback_links:
                parts.append(Markup("<p><b>Media (links):</b><br/>"))
                for label, url in fallback_links:
                    parts.append(
                        Markup(
                            f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(label)}</a><br/>'
                        )
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
                # Opportunities (same logic as calls)
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

                # Quotes
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

                # Post on ALL found opps and quotes
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
        p_from = self.env["quo.call"].sudo()._get_or_create_partner_for_phone(from_num, default_name="Unknown Caller") if from_num else self.env["res.partner"]
        p_to = self.env["quo.call"].sudo()._get_or_create_partner_for_phone(to_num, default_name="Unknown Caller") if to_num else self.env["res.partner"]

        direction = self.env["quo.call"].sudo()._normalize_direction(payload.get("direction"))

        created_at = payload.get("createdAt") or payload.get("created_at")
        dt_created = self.env["quo.call"].sudo()._parse_dt(created_at)

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
            "body": payload.get("body") or "",
            "media_json": json.dumps(media, ensure_ascii=False),
            "raw_message_json": json.dumps(payload, ensure_ascii=False),
        }

        if rec:
            rec.write({k: v for k, v in vals.items() if v not in (None, False, "") or k in ("raw_message_json", "media_json")})
            txt = rec
        else:
            txt = Text.create(vals)

        # Post chatter logs after upsert
        try:
            txt._post_to_related_documents_and_contacts()
        except Exception:
            _logger.exception("Failed to post QUO text %s to related documents/contacts", txt.id)

        return txt
