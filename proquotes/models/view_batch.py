# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import timedelta

class ProquotesViewBatch(models.Model):
    _name = "proquotes.view.batch"
    _description = "ProQuotes: Aggregated quote view events"
    _order = "send_at asc, id asc"

    sale_order_id = fields.Many2one(
        "sale.order", required=True, index=True, ondelete="cascade"
    )
    send_at = fields.Datetime(required=True, index=True)
    sent = fields.Boolean(default=False, index=True)
    event_ids = fields.One2many("proquotes.view.event", "batch_id", string="Events")

    @api.model
    def process_due_batches(self, limit=100):
        """Cron entry point: send aggregated notifications whose window ended."""
        now = fields.Datetime.now()
        batches = self.search([
            ("sent", "=", False),
            ("send_at", "<=", now),
        ], limit=limit)

        for batch in batches:
            order = batch.sale_order_id
            if not order:
                batch.write({"sent": True})
                continue

            # Recipients: salesperson if present
            recipient_ids = []
            if order.user_id and order.user_id.partner_id:
                recipient_ids.append(order.user_id.partner_id.id)

            # Build body with local times (salesperson tz if defined)
            # Fall back to current user's tz, then UTC.
            user_tz = (order.user_id and order.user_id.tz) or self.env.user.tz or "UTC"
            def _fmt(dt):
                local_dt = fields.Datetime.context_timestamp(self.with_context(tz=user_tz), dt)
                return local_dt.strftime("%H:%M")

            lines = []
            for ev in batch.event_ids.sorted("viewed_at"):
                when = _fmt(ev.viewed_at)
                who = ev.viewer_partner_id.display_name or (ev.viewer_email or _("Unknown"))
                lines.append(f"- {who} at {when}")

            if not lines:
                batch.write({"sent": True})
                continue

            header = _("Quote viewed by the following users (last 10 minutes):")
            body = header + "<br/>" + "<br/>".join(lines)

            order.with_context(mail_post_autofollow=True).message_post(
                body=body,
                message_type="comment",
                subtype_xmlid="sale.mt_order_viewed",  # keep same subtype for consistency
                partner_ids=list(set(recipient_ids)),
                author_id=(order.user_id.partner_id.id if order.user_id else False),
                subject=_("%s: quote views (batched)") % order.name,
            )

            # mark as sent (and you can optionally unlink the event rows)
            batch.write({"sent": True})
            # Optional cleanup:
            # batch.event_ids.unlink()


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
