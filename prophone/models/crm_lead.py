# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class CrmLead(models.Model):
    _inherit = "crm.lead"

    quo_can_send_text = fields.Boolean(compute="_compute_quo_can_send_text")

    def _sanitize_phone_to_e164ish(self, phone):
        """Same idea you used on partners: return +digits if possible."""
        if not phone:
            return False
        s = str(phone).strip()
        has_plus = s.startswith("+")
        digits = re.sub(r"\D+", "", s)
        if not digits:
            return False
        if has_plus:
            return "+" + digits
        if len(digits) >= 10:
            return "+" + digits
        return False

    def _lead_destination_phone(self):
        self.ensure_one()
        # Prefer lead phone/mobile, fallback to partner mobile/phone
        candidates = [
            getattr(self, "mobile", False),
            getattr(self, "phone", False),
            self.partner_id.mobile if self.partner_id else False,
            self.partner_id.phone if self.partner_id else False,
        ]
        for c in candidates:
            v = self._sanitize_phone_to_e164ish(c)
            if v:
                return v
        return False

    @api.depends("phone", "partner_id.phone", "partner_id.mobile")
    def _compute_quo_can_send_text(self):
        user = self.env.user
        allowed_ok = len(user.allowed_quo_phone_number_ids) >= 1

        for lead in self:
            lead.quo_can_send_text = bool(allowed_ok and lead._lead_destination_phone())

    def action_send_quo_text(self):
        """Server-side action used by the chatter button."""
        self.ensure_one()

        # Enforce same rules server-side (never trust only JS/UI)
        if len(self.env.user.allowed_quo_phone_number_ids) < 1:
            raise UserError(_("You do not have enough Quo numbers assigned to send texts (need at least 1)."))
        to_num = self._lead_destination_phone()
        if not to_num:
            raise UserError(_("This opportunity does not have a valid phone number to text."))

        return {
            "type": "ir.actions.act_window",
            "name": "Send Text",
            "res_model": "quo.send.text.wizard",
            "target": "new",

            "views": [(False, "form")],
            "view_mode": "form",

            "context": {
                "default_lead_id": self.id,
                "default_to_number": to_num,
            },
        }

    def quo_send_text_button_info(self):
        self.ensure_one()
        return {"can_send": bool(self.quo_can_send_text)}