# -*- coding: utf-8 -*-
import hmac, hashlib, json
from odoo import http, _
from odoo.http import request

class LeicaCallbackController(http.Controller):

    @http.route("/leica/callback", type="json", auth="public", methods=["POST"], csrf=False)
    def leica_callback(self, **kwargs):
        # Raw body + signature
        raw = request.httprequest.data or b""
        sig = request.httprequest.headers.get("X-Hub-Signature-256", "")
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            return {"ok": False, "error": "invalid-json"}

        # Verify HMAC
        ICP = request.env["ir.config_parameter"].sudo()
        secret = ICP.get_param("proleads_leica_webhook_secret") or ""
        good = f"sha256={hmac.new(secret.encode('utf-8'), raw, hashlib.sha256).hexdigest()}"
        if not secret or not hmac.compare_digest(sig or "", good):
            return {"ok": False, "error": "bad-signature"}

        lead_id = payload.get("lead_id")
        status  = (payload.get("status") or "").lower()  # "success" | "failed"
        error   = payload.get("error") or ""

        if not lead_id or status not in ("success", "failed"):
            return {"ok": False, "error": "bad-params"}

        Lead = request.env["crm.lead"].sudo().browse(int(lead_id))
        if not Lead.exists():
            return {"ok": False, "error": "lead-not-found"}

        vals = {
            "leica_registration_state": "success" if status == "success" else "failed",
            "leica_registered": (status == "success"),
            "leica_last_error": error or False,
        }
        Lead.write(vals)

        # Log in chatter
        if status == "success":
            Lead.message_post(body=_("Leica registration: SUCCESS."), message_type="comment",
                              subtype_xmlid="mail.mt_note")
        else:
            Lead.message_post(body=_("Leica registration: FAILED.<br/><br/>%s") % (error or _("Unknown error")),
                              message_type="comment", subtype_xmlid="mail.mt_note")

        return {"ok": True}
