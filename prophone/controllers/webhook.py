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

        obj_type = data_obj.get("object") if isinstance(data_obj, dict) else None

        _logger.info(
            "Quo webhook received event_type=%s data_object=%s",
            event_type,
            obj_type or type(data_obj),
        )

        try:
            # ------------------------------------------------------------
            # TEXT MESSAGES
            # ------------------------------------------------------------
            if event_type in ("message.received", "message.delivered") or obj_type == "message":
                if not isinstance(data_obj, dict):
                    return request.make_response("invalid message payload", status=400)

                message_id = data_obj.get("id")
                if not message_id:
                    _logger.warning("Quo webhook missing message id. payload=%s", payload)
                    return request.make_response("missing message id", status=400)

                request.env["quo.text"].sudo().upsert_text_from_payload(message_id, data_obj)
                return request.make_response("ok", status=200)

            # ------------------------------------------------------------
            # CALLS (recording / transcript / summary)
            # ------------------------------------------------------------
            call_id = False
            if isinstance(data_obj, dict):
                call_id = data_obj.get("id") or data_obj.get("callId")
                if not call_id and isinstance(data_obj.get("call"), dict):
                    call_id = data_obj["call"].get("id") or data_obj["call"].get("callId")

            if not call_id:
                _logger.warning("Quo webhook missing call id. payload=%s", payload)
                return request.make_response("missing call id", status=400)

            Call = request.env["quo.call"].sudo()

            # Ensure base call exists ONLY if payload looks like a call object
            if isinstance(data_obj, dict) and (
                data_obj.get("object") == "call" or any(k in data_obj for k in ("from", "to", "direction", "phoneNumberId"))
            ):
                Call.upsert_call_from_payload(call_id, data_obj)
            else:
                # Create a stub call if needed so transcript/summary can attach later
                if not Call.search([("quo_call_id", "=", call_id)], limit=1):
                    Call.create({"quo_call_id": call_id, "direction": "unknown"})

            # Route by event type
            if event_type == "call.transcript.completed":
                request.env["quo.call.transcript"].sudo().upsert_from_transcript_payload(call_id, data_obj)

            elif event_type == "call.summary.completed":
                Call.upsert_summary_from_payload(call_id, data_obj)

            elif event_type == "call.recording.completed":
                Call.upsert_recording_from_payload(call_id, data_obj)

            return request.make_response("ok", status=200)

        except Exception:
            _logger.exception("Failed processing Quo webhook. event_type=%s", event_type)
            return request.make_response("error", status=500)
