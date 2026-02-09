# -*- coding: utf-8 -*-
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class QuoWebhookController(http.Controller):

    @http.route("/quo/webhook", type="http", auth="public", csrf=False, methods=["POST"])
    def quo_webhook(self, **kwargs):
        raw = request.httprequest.data or b""

        # 1) Parse JSON safely
        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            _logger.exception("Quo webhook: invalid JSON body")
            return request.make_response("invalid json", status=400)

        # Helpful debug (you can keep this)
        _logger.info("Quo webhook received keys=%s", list(payload.keys()))

        # 2) Extract event type and call object (matches your sample payload)
        event_type = payload.get("type") or payload.get("event") or payload.get("eventType") or ""
        call_obj = (payload.get("data") or {}).get("object") or {}

        # Some providers wrap further; try one more level if needed
        if call_obj and isinstance(call_obj, dict) and call_obj.get("object") == "event" and "data" in call_obj:
            call_obj = (call_obj.get("data") or {}).get("object") or {}

        # 3) Only handle transcript completed (matches your UI checkbox: call.transcript.completed)
        if event_type == "call.transcript.completed":
            transcript = (call_obj.get("callTranscript") or {})
            request.env["quo.call.transcript"].sudo().upsert_from_transcript_payload(call_id, transcript)

        elif event_type == "call.summary.completed":
            request.env["quo.call"].sudo().upsert_summary_from_payload(call_id, call_obj)

        elif event_type == "call.recording.completed":
            request.env["quo.call"].sudo().upsert_recording_from_payload(call_id, call_obj)

        return "ok"

        # 4) Must have a call id
        call_id = call_obj.get("id")
        if not call_id:
            _logger.warning("Quo webhook missing call id. payload=%s", payload)
            return request.make_response("missing call id", status=400)

        try:
            # 5) Upsert call record using call object (direction, from/to, etc.)
            request.env["quo.call"].sudo().upsert_call_from_payload(call_id, call_obj)

            # 6) Build transcript payload from nested callTranscript object
            call_transcript = call_obj.get("callTranscript") or {}
            transcript_payload = {
                "callId": call_id,
                "createdAt": call_transcript.get("createdAt"),
                "duration": call_transcript.get("duration"),
                "status": call_obj.get("status"),
                "dialogue": call_transcript.get("dialogue") or [],
            }

            request.env["quo.call.transcript"].sudo().upsert_from_transcript_payload(call_id, transcript_payload)

            return request.make_response("ok", status=200)

        except Exception:
            # IMPORTANT: log full traceback so you can see it in Odoo logs
            _logger.exception("Failed processing Quo transcript webhook. call_id=%s", call_id)
            return request.make_response("error", status=500)
