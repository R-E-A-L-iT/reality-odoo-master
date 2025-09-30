# -*- coding: utf-8 -*-
import hmac, hashlib, json
from odoo import http, _
from odoo.http import request

class LeicaCallbackController(http.Controller):

    @http.route("/leica/callback", type="json", auth="public", methods=["POST"], csrf=False)
    def leica_callback(self, **kwargs):
        raw = request.httprequest.data or b""
        recv = request.httprequest.headers.get("X-Hub-Signature-256", "") or ""
        if recv.lower().startswith("sha256="):
            recv = recv[7:]

        ICP = request.env["ir.config_parameter"].sudo()
        secret = (ICP.get_param("proleads_leica_callback_secret") or "").strip()

        calc = hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()
        if not secret or not hmac.compare_digest(recv, calc):
            return {"ok": False, "error": "bad-signature"}

        payload = json.loads(raw.decode("utf-8"))
        lead_id = payload.get("lead_id")
        status  = (payload.get("status") or "").lower()
        error   = payload.get("error") or ""

        Lead = request.env["crm.lead"].sudo().browse(int(lead_id or 0))
        if not Lead.exists() or status not in ("success", "failed"):
            return {"ok": False, "error": "bad-params"}

        Lead.write({
            "leica_registration_state": "success" if status == "success" else "failed",
            "leica_registered": (status == "success"),
            "leica_last_error": error or False,
        })
        Lead.message_post(
            body=_("Leica registration: %s%s") % (
                "SUCCESS" if status == "success" else "FAILED",
                "" if status == "success" else f"<br/><br/>{error}"
            ),
            message_type="comment", subtype_xmlid="mail.mt_note"
        )
        return {"ok": True}
