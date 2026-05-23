# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError


_logger = logging.getLogger(__name__)

class QuoSendTextWizard(models.TransientModel):
    _name = "quo.send.text.wizard"
    _description = "Send Quo Text"

    partner_id = fields.Many2one("res.partner", string="Recipient")
    to_number = fields.Char(string="To", readonly=True)
    lead_id = fields.Many2one("crm.lead", readonly=True)
    sale_order_id = fields.Many2one("sale.order", readonly=True)
    ticket_id = fields.Many2one("helpdesk.ticket", readonly=True)

    from_number = fields.Selection(
        selection="_selection_from_numbers",
        string="Send From",
        required=True,
    )

    message = fields.Text(string="Message", required=True)

    def _get_quote_allowed_partner_ids(self):
        ids = self.env.context.get("quo_sms_partner_domain_ids") or []
        return set(ids)

    def _get_allowed_partner_ids(self):
        ids = self.env.context.get("quo_sms_partner_domain_ids") or []
        return set(ids)

    @api.model
    def _selection_from_numbers(self):
        Call = self.env["quo.call"].sudo()

        # Ensure local phone number table is up-to-date
        Call._quo_sync_phone_numbers()


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

        # 1) If lead or sales order is provided, use it
        lead_id = self.env.context.get("default_lead_id")
        if lead_id:
            lead = self.env["crm.lead"].browse(int(lead_id))
            if lead.exists():
                # if context already provides to_number, use it
                to_num = self.env.context.get("default_to_number")
                if not to_num:
                    # fallback (mirrors crm.lead helper)
                    to_num = lead._lead_destination_phone()
                if not to_num:
                    raise UserError(_("This opportunity has no valid phone number."))
                vals.update({
                    "lead_id": lead.id,
                    "to_number": to_num,
                    "partner_id": lead.partner_id.id if lead.partner_id else False,
                })
                return vals

        sale_order_id = self.env.context.get("default_sale_order_id")
        if sale_order_id:
            order = self.env["sale.order"].browse(int(sale_order_id))
            if order.exists():
                vals["sale_order_id"] = order.id

                # if context already provided a partner/to_number, keep them
                partner_id = self.env.context.get("default_partner_id")
                to_num = self.env.context.get("default_to_number")
                if partner_id:
                    vals["partner_id"] = int(partner_id)
                if to_num:
                    vals["to_number"] = to_num

                return vals

        ticket_id = self.env.context.get("default_ticket_id")
        if ticket_id:
            ticket = self.env["helpdesk.ticket"].browse(int(ticket_id))
            if ticket.exists():
                vals["ticket_id"] = ticket.id

                partner_id = self.env.context.get("default_partner_id")
                to_num = self.env.context.get("default_to_number")
                if partner_id:
                    vals["partner_id"] = int(partner_id)
                if to_num:
                    vals["to_number"] = to_num

                return vals

        # 2) Otherwise fallback to partner flow (your existing behavior)
        partner_id = self.env.context.get("default_partner_id") or self.env.context.get("active_id")
        partner = self.env["res.partner"].browse(int(partner_id)) if partner_id else self.env["res.partner"]
        if partner and partner.exists():
            to_num = partner._sanitize_phone(partner.mobile) or partner._sanitize_phone(partner.phone)
            if not to_num:
                raise UserError(_("This contact has no valid phone number (phone/mobile)."))
            vals.update({
                "partner_id": partner.id,
                "to_number": to_num,
            })
        return vals

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for w in self:
            if not w.partner_id:
                w.to_number = False
                continue

            # Try mobile then phone, sanitize to E.164-ish
            to_num = w.partner_id.mobile or w.partner_id.phone
            if hasattr(w.partner_id, "_sanitize_phone"):
                w.to_number = w.partner_id._sanitize_phone(to_num)
            else:
                # fallback: minimal sanitizer
                digits = "".join(ch for ch in (to_num or "") if ch.isdigit())
                w.to_number = ("+" + digits) if digits else False

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

        # If sending from a quote, enforce recipient is in allowed follower list
        if self.sale_order_id or self.ticket_id:
            allowed_ids = self._get_allowed_partner_ids()
            if not self.partner_id or self.partner_id.id not in allowed_ids:
                raise UserError(_("Please select a valid recipient from the followers list."))

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
