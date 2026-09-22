import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PromessagingInbound(http.Controller):
    """Where an AI posts its answers back into Odoo."""

    @http.route("/promessaging/webhook/reply", type="json", auth="none", methods=["POST"], csrf=False)
    def webhook_reply(self, **payload):
        payload = payload or {}
        env = request.env(user=1)  # authenticated by the sub-user's reply key
        Subuser = env["promessaging.subuser"].sudo()

        key = payload.get("key") or self._bearer_token()
        subuser = Subuser._authenticate_inbound(payload.get("subuser"), key)
        if not subuser:
            return {"ok": False, "error": "invalid_key"}

        message = payload.get("message") or payload.get("reply") or payload.get("text")
        # a plan or summary update carries no message of its own
        if not message and not payload.get("plan") and not payload.get("summary"):
            return {"ok": False, "error": "missing_message"}

        try:
            return subuser._receive_reply(
                message,
                chat_id=payload.get("chat_id"),
                draft_id=payload.get("draft_id"),
                objective_id=payload.get("objective_id"),
                plan=payload.get("plan"),
                summary_id=payload.get("summary_id"),
                summary_values=payload.get("summary"),
                user_id=payload.get("user_id"),
                user_login=payload.get("user_login"),
                thread_model=payload.get("thread_model"),
                thread_id=payload.get("thread_id"),
            )
        except Exception as error:
            _logger.exception("ProMessaging: inbound reply from ~%s failed", subuser.handle)
            return {"ok": False, "error": str(error)}

    def _bearer_token(self):
        header = request.httprequest.headers.get("Authorization") or ""
        if header.lower().startswith("bearer "):
            return header[7:].strip()
        return header.strip() or None
