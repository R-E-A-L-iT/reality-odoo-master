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

        _logger.info("Quo webhook received keys=%s", list(payload.keys()))

        # 2) Extract event type and call object
        event_type = payload.get("type") or payload.get("event") or payload.get("eventType") or ""
        call_obj = (payload.get("data") or {}).get("object") or {}

        # If provider wraps differently, try one more level
        if isinstance(call_obj, dict) and call_obj.get("object") == "event" and "data" in call_obj:
            call_obj = (call_obj.get("data") or {}).get("object") or {}

        # 3) Must have a call id
        call_id = (call_obj or {}).get("id")
        if not call_id:
            _logger.warning("Quo webhook missing call id. payload=%s", payload)
            return request.make_response("missing call id", status=400)

        try:
            # 4) Always upsert the base call first
            request.env["quo.call"].sudo().upsert_call_from_payload(call_id, call_obj)

            # 5) Route by event type
            if event_type == "call.transcript.completed":
                transcript = call_obj.get("callTranscript") or {}
                request.env["quo.call.transcript"].sudo().upsert_from_transcript_payload(call_id, transcript)

            elif event_type == "call.summary.completed":
                request.env["quo.call"].sudo().upsert_summary_from_payload(call_id, call_obj)

            elif event_type == "call.recording.completed":
                request.env["quo.call"].sudo().upsert_recording_from_payload(call_id, call_obj)

            # Unknown events: accept but do nothing
            return request.make_response("ok", status=200)

        except Exception:
            _logger.exception("Failed processing Quo webhook. call_id=%s event_type=%s", call_id, event_type)
            return request.make_response("error", status=500)
