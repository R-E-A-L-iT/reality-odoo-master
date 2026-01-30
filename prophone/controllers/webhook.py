# -*- coding: utf-8 -*-
import base64
import binascii
import hmac
import hashlib
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _parse_signature_header(header_value):
    """
    Expected formats:
      - "t=...,v1=<hex>"
      - "<hex>"
    Returns (timestamp_str_or_None, signature_hex)
    """
    if not header_value:
        return (None, "")
    hv = header_value.strip()
    if "v1=" in hv:
        ts = None
        sig = ""
        parts = [p.strip() for p in hv.split(",")]
        for p in parts:
            if p.startswith("t="):
                ts = p.split("=", 1)[1].strip()
            elif p.startswith("v1="):
                sig = p.split("=", 1)[1].strip()
        return (ts, sig)
    return (None, hv)



class QuoWebhookController(http.Controller):

    @http.route("/quo/webhook", type="http", auth="public", csrf=False, methods=["POST"])
    def quo_webhook(self, **kwargs):
        raw = request.httprequest.data or b""
        sig_header = request.httprequest.headers.get("openphone-signature", "")
        ts, sig = _parse_signature_header(sig_header)

        secret = request.env["ir.config_parameter"].sudo().get_param("quo_transcripts.webhook_secret") or ""
        if secret:
            # Key can be raw text or base64-encoded. Try both.
            candidate_keys = [secret.encode("utf-8")]
            try:
                candidate_keys.append(base64.b64decode(secret))
            except (binascii.Error, ValueError):
                pass

            # Message can be raw body or "t.body"
            candidate_msgs = [raw]
            if ts:
                candidate_msgs.append((ts + ".").encode("utf-8") + raw)

            valid = False
            for key in candidate_keys:
                for msg in candidate_msgs:
                    expected = hmac.new(key, msg=msg, digestmod=hashlib.sha256).hexdigest()
                    if hmac.compare_digest(expected, sig):
                        valid = True
                        break
                if valid:
                    break

            if not valid:
                _logger.warning("Quo webhook signature invalid. header=%s", sig_header)
                return request.make_response("invalid signature", status=401)

        # Best-effort event extraction
        event_type = payload.get("type") or payload.get("event") or payload.get("eventType") or ""
        data_obj = (payload.get("data") or {}).get("object") or payload.get("data") or {}

        # We care about transcript completion
        if event_type == "call.transcript.completed":
            call_id = data_obj.get("id")
            if not call_id:
                return request.make_response("missing call id", status=400)

            # upsert call from call object
            request.env["quo.call"].sudo().upsert_call_from_payload(call_id, data_obj)

            # build transcript payload from nested callTranscript
            call_transcript = data_obj.get("callTranscript") or {}
            transcript_payload = {
                "callId": call_id,
                "createdAt": call_transcript.get("createdAt"),
                "duration": call_transcript.get("duration"),
                "status": data_obj.get("status"),
                "dialogue": call_transcript.get("dialogue") or [],
            }
            request.env["quo.call.transcript"].sudo().upsert_from_transcript_payload(call_id, transcript_payload)

            return request.make_response("ok", status=200)
