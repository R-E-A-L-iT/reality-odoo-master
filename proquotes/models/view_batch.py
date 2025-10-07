# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta
import logging

_logger = logging.getLogger(__name__)

class ProquotesViewBatch(models.Model):
    _name = "proquotes.view.batch"
    _description = "ProQuotes: Aggregated quote view events"
    _order = "send_at asc, id asc"

    sale_order_id = fields.Many2one("sale.order", required=True, index=True, ondelete="cascade")
    send_at = fields.Datetime(required=True, index=True)
    sent = fields.Boolean(default=False, index=True)
    event_ids = fields.One2many("proquotes.view.event", "batch_id", string="Events")

    @api.model
    def process_due_batches(self, limit=100, force=False):
        """
        Cron (and manual) entry point.
        - Normal mode: send batches where send_at <= now and not sent.
        - force=True: ignore send_at (useful for testing immediately after viewing).
        """
        now = fields.Datetime.now()
        domain = [("sent", "=", False)]
        if not force:
            domain.append(("send_at", "<=", now))

        batches = self.search(domain, limit=limit)
        _logger.info("ProQuotes: processing %s batche(s), force=%s", len(batches), force)

        for batch in batches:
            try:
                order = batch.sale_order_id
                if not order:
                    _logger.warning("ProQuotes: batch %s has no order; marking sent", batch.id)
                    batch.sent = True
                    continue

                events = batch.event_ids.sorted("viewed_at")
                if not events:
                    _logger.info("ProQuotes: batch %s has no events; marking sent", batch.id)
                    batch.sent = True
                    continue

                # Build recipients: salesperson + followers (with email)
                recipient_partners = self.env["res.partner"]
                if order.user_id and order.user_id.partner_id and order.user_id.partner_id.email:
                    recipient_partners |= order.user_id.partner_id

                follower_partners = order.message_follower_ids.mapped("partner_id")
                follower_partners = follower_partners.filtered(lambda p: p.email)
                recipient_partners |= follower_partners

                # De-dup recipients
                recipient_ids = list(set(recipient_partners.ids))
                if not recipient_ids:
                    _logger.warning("ProQuotes: batch %s has no recipients; marking sent", batch.id)
                    batch.sent = True
                    continue

                # Format lines in salesperson's tz (fallback to current user tz or UTC)
                user_tz = (order.user_id and order.user_id.tz) or self.env.user.tz or "UTC"

                def _fmt(dt):
                    local_dt = fields.Datetime.context_timestamp(self.with_context(tz=user_tz), dt)
                    return local_dt.strftime("%H:%M")

                lines = []
                for ev in events:
                    when = _fmt(ev.viewed_at)
                    who = ev.viewer_partner_id.display_name or (ev.viewer_email or _("Unknown"))
                    lines.append(f"- {who} at {when}")

                header = _("Quote viewed by the following users (last 10 minutes):")
                body = header + "<br/>" + "<br/>".join(lines)

                _logger.info(
                    "ProQuotes: posting batched notice for order %s to %d recipients; %d event(s).",
                    order.name, len(recipient_ids), len(events)
                )

                # Force email notification; don't auto-follow extra people
                order.with_context(
                    mail_notify_force_send=True,
                    mail_create_nosubscribe=True,
                ).message_post(
                    body=body,
                    message_type="comment",
                    subtype_xmlid="sale.mt_order_viewed",  # keep same subtype
                    partner_ids=recipient_ids,
                    subject=_("%s: quote views (batched)") % order.name,
                    # author_id left as default (cron user) to avoid oddities
                )

                # mark as sent; keep history (or unlink if you prefer)
                batch.sent = True

            except Exception as e:
                _logger.exception("ProQuotes: error processing batch %s: %s", batch.id, e)
                # Do not mark sent so retry can happen next run.


class ProquotesViewEvent(models.Model):
    _name = "proquotes.view.event"
    _description = "ProQuotes: Single quote view event"
    _order = "viewed_at asc, id asc"

    batch_id = fields.Many2one(
        "proquotes.view.batch", required=True, index=True, ondelete="cascade"
    )
    viewer_partner_id = fields.Many2one("res.partner", required=True, index=True)
    viewer_email = fields.Char()
    viewed_at = fields.Datetime(required=True, default=fields.Datetime.now)
