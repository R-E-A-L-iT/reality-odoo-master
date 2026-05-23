# -*- coding: utf-8 -*-

import json
from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)



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
