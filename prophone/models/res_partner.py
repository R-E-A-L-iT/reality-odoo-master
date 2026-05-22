# -*- coding: utf-8 -*-
import re
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    quo_calls_count = fields.Integer(compute="_compute_quo_calls_count")
    quo_texts_count = fields.Integer(compute="_compute_quo_texts_count")

    quo_contact_id = fields.Char(string="Quo Contact ID", index=True)
    quo_contact_source_url = fields.Char(string="Quo Contact URL")

    quo_has_valid_phone = fields.Boolean(
        compute="_compute_quo_has_valid_phone",
        string="Has Valid SMS Phone",
    )

    quo_can_send_text = fields.Boolean(
        compute="_compute_quo_can_send_text",
        string="Can Send Text"
    )

    def _compute_quo_can_send_text(self):
        user = self.env.user
        has_numbers = bool(user.allowed_quo_phone_number_ids)

        for partner in self:
            partner.quo_can_send_text = bool(
                has_numbers and partner.quo_has_valid_phone
            )

    def _sanitize_phone(self, phone):
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
        return digits

    def _get_quo_phone_candidates(self):
        """Return a list of sanitized phone candidates for matching."""
        self.ensure_one()
        candidates = set()
        for val in (self.phone, self.mobile):
            sv = self._sanitize_phone(val)
            if sv:
                candidates.add(sv)
        return list(candidates)

    def _compute_quo_has_valid_phone(self):
        """Used to show/hide the Send Text button.

        Consider a phone valid if it normalizes to E.164-ish:
        - starts with '+'
        - 10 to 15 digits
        """
        for partner in self:
            ok = False
            for cand in partner._get_quo_phone_candidates():
                if not cand or not cand.startswith("+"):
                    continue
                digits = re.sub(r"\D+", "", cand)
                if 10 <= len(digits) <= 15:
                    ok = True
                    break
            partner.quo_has_valid_phone = ok

    def _compute_quo_calls_count(self):
        Call = self.env["quo.call"].sudo()
        for partner in self:
            phones = partner._get_quo_phone_candidates()
            if not phones:
                partner.quo_calls_count = 0
                continue
            domain = ["|", ("from_sanitized", "in", phones), ("to_sanitized", "in", phones)]
            partner.quo_calls_count = Call.search_count(domain)

    def _compute_quo_texts_count(self):
        Text = self.env["quo.text"].sudo()
        for partner in self:
            phones = partner._get_quo_phone_candidates()
            if not phones:
                partner.quo_texts_count = 0
                continue
            domain = ["|", ("from_sanitized", "in", phones), ("to_sanitized", "in", phones)]
            partner.quo_texts_count = Text.search_count(domain)

    def action_view_quo_calls(self):
        self.ensure_one()
        phones = self._get_quo_phone_candidates()
        domain = []
        if phones:
            domain = ["|", ("from_sanitized", "in", phones), ("to_sanitized", "in", phones)]
        return {
            "type": "ir.actions.act_window",
            "name": "Calls",
            "res_model": "quo.call",
            "view_mode": "tree,form",
            "domain": domain,
            "context": {
                "search_default_group_by_direction": 0,
            },
        }
    
    def quo_send_text_button_info(self):
        self.ensure_one()
        # Use the same booleans you already had for the old button
        return {"can_send": bool(getattr(self, "quo_has_valid_phone", False) and getattr(self, "quo_can_send_text", False))}

    def action_view_quo_texts(self):
        self.ensure_one()
        phones = self._get_quo_phone_candidates()
        domain = []
        if phones:
            domain = ["|", ("from_sanitized", "in", phones), ("to_sanitized", "in", phones)]
        return {
            "type": "ir.actions.act_window",
            "name": "Texts",
            "res_model": "quo.text",
            "view_mode": "tree,form",
            "domain": domain,
        }

    def action_send_quo_text(self):
        """Open the Send Text wizard for this partner."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Send Text",
            "res_model": "quo.send.text.wizard",
            "target": "new",
            "views": [(False, "form")],
            "view_mode": "form",
            "context": {
                "default_partner_id": self.id,
            },
        }