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

        # QUO v3 typically wraps everything under {"object": {"object": "event", ...}}
        event = payload.get("object") if isinstance(payload.get("object"), dict) else payload
        if not (isinstance(event, dict) and event.get("object") == "event" and "data" in event):
            # Some providers may post the event dict directly at top-level
            event = payload

        event_type = event.get("type") or event.get("event") or event.get("eventType") or ""
        data_obj = (event.get("data") or {}).get("object") or {}

        _logger.info(
            "Quo webhook received event_type=%s data_object=%s keys=%s",
            event_type,
            (data_obj.get("object") if isinstance(data_obj, dict) else type(data_obj)),
            list(event.keys()) if isinstance(event, dict) else [],
        )

        # 2) Resolve call id across different event object shapes
        call_id = False
        if isinstance(data_obj, dict):
            call_id = data_obj.get("id") or data_obj.get("callId")
            # Defensive fallback if QUO ever nests it
            if not call_id and isinstance(data_obj.get("call"), dict):
                call_id = data_obj["call"].get("id") or data_obj["call"].get("callId")

        if not call_id:
            _logger.warning("Quo webhook missing call id. payload=%s", payload)
            return request.make_response("missing call id", status=400)

        try:
            Call = request.env["quo.call"].sudo()

            # 3) Ensure the base call exists.
            # Only upsert full call details when the payload is actually a call object.
            # Transcript/Summary payloads are different objects and don't include from/to/direction reliably.
            if isinstance(data_obj, dict) and (
                data_obj.get("object") == "call" or any(k in data_obj for k in ("from", "to", "direction", "phoneNumberId"))
            ):
                Call.upsert_call_from_payload(call_id, data_obj)
            else:
                # Create a stub call if needed so transcript/summary can attach later
                if not Call.search([("quo_call_id", "=", call_id)], limit=1):
                    Call.create({"quo_call_id": call_id, "direction": "unknown"})

            # 4) Route by event type
            if event_type == "call.transcript.completed":
                # data_obj is a callTranscript object that includes callId, dialogue, etc.
                request.env["quo.call.transcript"].sudo().upsert_from_transcript_payload(call_id, data_obj)

            elif event_type == "call.summary.completed":
                # data_obj is a callSummary object (object=callSummary, callId=...)
                Call.upsert_summary_from_payload(call_id, data_obj)

            elif event_type == "call.recording.completed":
                # data_obj is a call object with media[0]
                Call.upsert_recording_from_payload(call_id, data_obj)

            # Unknown events: accept but do nothing
            return request.make_response("ok", status=200)

        except Exception:
            _logger.exception("Failed processing Quo webhook. call_id=%s event_type=%s", call_id, event_type)
            return request.make_response("error", status=500)
