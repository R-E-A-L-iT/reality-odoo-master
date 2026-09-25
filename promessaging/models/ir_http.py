from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        user = self.env.user
        if user._is_internal():
            result["can_send_message"] = user.can_send_message
            # the composer suggests people it already knows about, client-side,
            # so the browser has to know who may not be pinged
            blocked = self.env["res.users"].sudo().search([("no_ping", "=", True)])
            result["promessaging_no_ping_partner_ids"] = blocked.partner_id.ids
        return self._promessaging_limit_companies(result)

    def _promessaging_limit_companies(self, session_info):
        """Hide companies the acting sub-user may not work in."""
        subuser = self.env["promessaging.subuser"]._active_subuser()
        allowed = subuser._effective_companies() if subuser else None
        companies = session_info.get("user_companies")
        if not allowed or not companies:
            return session_info
        allowed_ids = set(allowed.ids) & set(self.env.user._get_company_ids())
        companies["allowed_companies"] = {
            cid: values
            for cid, values in companies.get("allowed_companies", {}).items()
            if cid in allowed_ids
        }
        if companies.get("current_company") not in allowed_ids:
            default = subuser.sudo().company_id.id
            companies["current_company"] = (
                default if default in allowed_ids else (min(allowed_ids) if allowed_ids else None)
            )
        session_info["display_switch_company_menu"] = (
            session_info.get("display_switch_company_menu")
            and len(companies["allowed_companies"]) > 1
        )
        return session_info
