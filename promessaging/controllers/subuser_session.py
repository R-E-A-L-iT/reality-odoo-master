from odoo import http
from odoo.http import request

SESSION_KEY = "promessaging_subuser_id"


class PromessagingSubuserSession(http.Controller):
    """Choosing which AI sub-user this browser session is acting as."""

    @http.route("/promessaging/subuser/state", type="json", auth="user")
    def subuser_state(self):
        return request.env["promessaging.subuser"].get_session_state()

    @http.route("/promessaging/subuser/select", type="json", auth="user")
    def subuser_select(self, subuser_id, pin):
        Subuser = request.env["promessaging.subuser"]
        subuser = Subuser._verify_pin(subuser_id, pin)
        if not subuser:
            return {"ok": False, "error": "invalid_pin"}
        request.session[SESSION_KEY] = subuser.id
        return {"ok": True, "state": Subuser.get_session_state()}

    @http.route("/promessaging/subuser/clear", type="json", auth="user")
    def subuser_clear(self):
        request.session.pop(SESSION_KEY, None)
        return request.env["promessaging.subuser"].get_session_state()
