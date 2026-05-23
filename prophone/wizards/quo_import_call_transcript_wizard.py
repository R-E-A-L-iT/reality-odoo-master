# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.exceptions import UserError


class QuoImportCallTranscriptWizard(models.TransientModel):
    _name = "quo.import.call.transcript.wizard"
    _description = "Import Quo Call Transcript"

    quo_call_id = fields.Char(string="Quo Call ID", required=True)

    def action_import(self):
        self.ensure_one()
        call_id = (self.quo_call_id or "").strip()
        if not call_id:
            raise UserError(_("Please enter a Quo Call ID."))

        Call = self.env["quo.call"].sudo()
        Transcript = self.env["quo.call.transcript"].sudo()

        # Fetch transcript from API
        # Endpoint shown in docs: GET /v1/call-transcripts/{id}
        payload = Call._quo_get(f"call-transcripts/{call_id}")

        # Some APIs wrap response (best-effort)
        transcript_obj = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
        if not isinstance(transcript_obj, dict):
            raise UserError(_("Unexpected API response for transcript."))

        # Ensure we have a call record
        Call.upsert_call_from_payload(call_id, transcript_obj)

        # Store transcript
        Transcript.upsert_from_transcript_payload(call_id, transcript_obj)

        return {"type": "ir.actions.act_window_close"}
