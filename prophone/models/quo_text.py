# -*- coding: utf-8 -*-

import json
import base64
from markupsafe import Markup, escape
import requests
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)



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
        p_from = self.env["quo.call"].sudo()._get_or_create_partner_for_phone(from_num, default_name="Unknown Caller") if from_num else self.env["res.partner"]
        p_to = self.env["quo.call"].sudo()._get_or_create_partner_for_phone(to_num, default_name="Unknown Caller") if to_num else self.env["res.partner"]

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
