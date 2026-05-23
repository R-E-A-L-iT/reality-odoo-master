# -*- coding: utf-8 -*-

import re
from odoo import models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _sanitize_phone_to_e164ish(self, phone):
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

    def _quo_sms_candidate_partners(self):
        """External followers of the quote with a valid phone/mobile."""
        self.ensure_one()

        # Followers partner list
        partners = self.message_follower_ids.mapped("partner_id")

        def is_external(p):
            # Exclude internal users: partners linked to any internal user (share=False)
            # Portal users have share=True and are allowed.
            internal_users = p.user_ids.filtered(lambda u: not u.share)
            return not internal_users

        def has_valid_phone(p):
            return bool(
                self._sanitize_phone_to_e164ish(p.mobile) or self._sanitize_phone_to_e164ish(p.phone)
            )

        partners = partners.filtered(lambda p: is_external(p) and has_valid_phone(p))
        return partners

    def quo_send_text_button_info(self):
        """RPC used by chatter to decide visibility."""
        self.ensure_one()
        allowed_ok = len(self.env.user.allowed_quo_phone_number_ids) >= 1
        has_recipient = bool(self._quo_sms_candidate_partners())
        return {"can_send": bool(allowed_ok and has_recipient)}

    def action_send_quo_text(self):
        """Open send-text wizard from a quote."""
        self.ensure_one()

        if len(self.env.user.allowed_quo_phone_number_ids) < 1:
            raise UserError(_("You do not have any Quo numbers assigned to send texts."))

        recipients = self._quo_sms_candidate_partners()
        if not recipients:
            raise UserError(_("No eligible quote followers have a valid phone number (and are not internal users)."))

        # preselect the first eligible recipient
        default_partner = recipients[0]
        to_num = self._sanitize_phone_to_e164ish(default_partner.mobile) or self._sanitize_phone_to_e164ish(default_partner.phone)

        return {
            "type": "ir.actions.act_window",
            "name": "Send Text",
            "res_model": "quo.send.text.wizard",
            "target": "new",
            "views": [(False, "form")],   # IMPORTANT: avoids action.views.map crash
            "view_mode": "form",
            "context": {
                "default_sale_order_id": self.id,
                "default_partner_id": default_partner.id,
                "default_to_number": to_num,
                # used by wizard domain for recipient selection
                "quo_sms_partner_domain_ids": recipients.ids,
            },
        }
