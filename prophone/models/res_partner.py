# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    quo_calls_count = fields.Integer(compute="_compute_quo_calls_count")
    quo_texts_count = fields.Integer(compute="_compute_quo_texts_count")

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
