# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class QuoSendTextWizard(models.TransientModel):
    _name = "quo.send.text.wizard"
    _description = "Send Quo Text"

    partner_id = fields.Many2one("res.partner", required=True, readonly=True)
    to_number = fields.Char(string="To", required=True, readonly=True)

    from_number = fields.Selection(
        selection="_selection_from_numbers",
        string="Send From",
        required=True,
    )

    message = fields.Text(string="Message", required=True)

    @api.model
    def _selection_from_numbers(self):
        Call = self.env["quo.call"].sudo()

        # Ensure local phone number table is up-to-date
        Call._quo_sync_phone_numbers()

        Phone = self.env["quo.phone.number"].sudo()

        user = self.env.user
        allowed = user.allowed_quo_phone_number_ids

        # If admin and no restriction set, allow all active numbers
        allowed = user.allowed_quo_phone_number_ids.filtered(lambda r: r.active)
        recs = allowed  # no fallback

        options = []
        for r in recs:
            options.append((r.quo_id, r.display_name))  # value = PNxxxx

        options.sort(key=lambda x: x[1] or "")
        return options

    @api.model
    def default_get(self, fields_list):
        vals = super().default_get(fields_list)

        partner_id = self.env.context.get("default_partner_id") or self.env.context.get("active_id")
        partner = self.env["res.partner"].browse(int(partner_id)) if partner_id else self.env["res.partner"]
        if not partner or not partner.exists():
            return vals

        to_num = partner._sanitize_phone(partner.mobile) or partner._sanitize_phone(partner.phone)
        if not to_num:
            raise UserError(_("This contact has no valid phone number (phone/mobile)."))

        vals.update({
            "partner_id": partner.id,
            "to_number": to_num,
        })
        return vals

    def action_send(self):
        self.ensure_one()

        msg = (self.message or "").strip()
        if not msg:
            raise UserError(_("Please enter a message."))
        if len(msg) > 1600:
            raise UserError(_("Message is too long (max 1600 characters)."))

        from_num = (self.from_number or "").strip()
        to_num = (self.to_number or "").strip()
        if not from_num or not to_num:
            raise UserError(_("Missing from/to numbers."))

        Call = self.env["quo.call"].sudo()

        payload = {
            "content": msg,
            "from": from_num,
            "to": [to_num],
        }

        resp = Call._quo_post("messages", payload)
        data = resp.get("data") if isinstance(resp, dict) else None

        if not self.from_number:
            raise UserError(_("You do not have any Quo numbers assigned. Ask an administrator to assign one."))

        # Best-effort: create/update quo.text immediately
        if isinstance(data, dict) and data.get("id"):
            try:
                self.env["quo.text"].sudo().upsert_text_from_payload(data["id"], data)
            except Exception:
                _logger.exception("Failed to upsert sent message into quo.text")

        return {"type": "ir.actions.act_window_close"}