# -*- coding: utf-8 -*-
import hmac
import hashlib
import json
import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


def _extract_v1_signature(header_value):
    """
    Supports formats like:
      - "t=...,v1=<hex>"
      - "<hex>"
    """
    if not header_value:
        return ""
    hv = header_value.strip()
    if "v1=" in hv:
        parts = [p.strip() for p in hv.split(",")]
        for p in parts:
            if p.startswith("v1="):
                return p.split("=", 1)[1].strip()
    return hv


class QuoWebhookController(http.Controller):

    @http.route("/quo/webhook", type="http", auth="public", csrf=False, methods=["POST"])
    def quo_webhook(self, **kwargs):
        raw = request.httprequest.data or b""
        sig_header = request.httprequest.headers.get("openphone-signature", "")
        v1_sig = _extract_v1_signature(sig_header)

        secret = request.env["ir.config_parameter"].sudo().get_param("quo_transcripts.webhook_secret") or ""
        if secret:
            expected = hmac.new(
                secret.encode("utf-8"),
                msg=raw,
                digestmod=hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(expected, v1_sig):
                _logger.warning("Quo webhook signature invalid. expected=%s got=%s", expected, v1_sig)
                return request.make_response("invalid signature", status=401)

        try:
            payload = json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            _logger.exception("Quo webhook: invalid JSON")
            return request.make_response("invalid json", status=400)

        # Best-effort event extraction
        event = payload.get("event") or payload.get("type") or ""
        data = payload.get("data") or payload.get("payload") or payload

        # We care about transcript completion
        if event == "call.transcript.completed":
            try:
                # data may already be transcript object including callId/dialogue
                call_id = data.get("callId") or data.get("call_id")
                if not call_id:
                    return request.make_response("missing callId", status=400)

                # Upsert call (may contain contactIds, etc.)
                request.env["quo.call"].sudo().upsert_call_from_payload(call_id, data)

                # Store transcript + dialogue
                request.env["quo.call.transcript"].sudo().upsert_from_transcript_payload(call_id, data)

                return request.make_response("ok", status=200)
            except Exception:
                _logger.exception("Failed processing transcript webhook")
                return request.make_response("error", status=500)

        # Ignore other events (but acknowledge)
        return request.make_response("ignored", status=200)
