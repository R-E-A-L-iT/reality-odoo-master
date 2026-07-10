# -*- coding: utf-8 -*-
"""Rental date-request availability analysis.

When a customer presses "Request dates" on the quote portal, this posts an
internal, salesperson-tagged note summarising whether the requested rental
window is realistic: enough stock, conflicts with confirmed reservations,
competing unconfirmed requests, and shipping lead time.

Rental quote lines are often phantom-BOM kits; what actually ships (and what
must be in stock) are the kit's component products. Availability is therefore
computed against the exploded components, mirroring `_build_rental_move_vals`.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from markupsafe import Markup

from odoo import _, fields, models
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)

# Average shipping time each way, in days.
SHIPPING_DAYS_MIN = 3
SHIPPING_DAYS_MAX = 4

_STATUS_STYLE = {
    "ok": ("#0a7d33", "✔ OK"),
    "risk": ("#b26a00", "⚠ Tight"),
    "short": ("#b00020", "✖ Short"),
    "na": ("#777777", "— n/a"),
}


def _fmt_qty(value):
    value = value or 0.0
    return str(int(value)) if float(value).is_integer() else ("%.2f" % value)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ------------------------------------------------------------------
    # Requirements (real shipped products, phantom-BOM kits exploded)
    # ------------------------------------------------------------------
    def _rental_component_requirements(self):
        """Return {product.product: qty} of the actual products that ship for
        this rental — kits exploded into their components, mirroring
        `_build_rental_move_vals`."""
        self.ensure_one()
        reqs = defaultdict(float)
        for line in self.order_line:
            if line.display_type or line.x_is_rental_kit_component:
                continue
            if (line.selected or "") != "true" or not line.product_id:
                continue
            bom = self._get_phantom_bom_for_line(line)
            if bom:
                for bom_line in bom.bom_line_ids:
                    comp = bom_line.product_id
                    qty = bom_line.product_qty * (line.product_uom_qty or 1.0)
                    if comp and qty > 0:
                        reqs[comp] += qty
            else:
                qty = line.product_uom_qty or 0.0
                if qty > 0:
                    reqs[line.product_id] += qty
        return reqs

    def _rental_overlapping_orders(self, buffer_days=SHIPPING_DAYS_MAX):
        """Other rental orders whose window overlaps this one's (padded by the
        shipping buffer on each side). Returns (confirmed, requested)."""
        self.ensure_one()
        Order = self.env["sale.order"].sudo()
        empty = Order.browse()
        if not (self.rental_start_date and self.rental_return_date):
            return empty, empty
        start = fields.Datetime.to_datetime(self.rental_start_date) - timedelta(days=buffer_days)
        end = fields.Datetime.to_datetime(self.rental_return_date) + timedelta(days=buffer_days)
        base = [
            ("id", "!=", self.id),
            ("is_rental_order", "=", True),
            ("rental_start_date", "!=", False),
            ("rental_return_date", "!=", False),
            ("rental_start_date", "<=", end),
            ("rental_return_date", ">=", start),
        ]
        confirmed = Order.search(base + [("state", "in", ["sale", "done"])])
        requested = Order.search(base + [("state", "in", ["draft", "sent"])])
        return confirmed, requested

    def _rental_availability_rows(self):
        """Per-component availability for the requested window."""
        self.ensure_one()
        reqs = self._rental_component_requirements()
        confirmed_orders, requested_orders = self._rental_overlapping_orders()

        conf_by_product = defaultdict(float)
        for other in confirmed_orders:
            for product, qty in other._rental_component_requirements().items():
                conf_by_product[product] += qty
        req_by_product = defaultdict(float)
        for other in requested_orders:
            for product, qty in other._rental_component_requirements().items():
                req_by_product[product] += qty

        wh_id = self.warehouse_id.id
        rows = []
        for product, need in sorted(reqs.items(), key=lambda kv: kv[0].display_name.lower()):
            stockable = product.type == "product"
            on_hand = (product.with_context(warehouse=wh_id).qty_available if wh_id
                       else product.qty_available) if stockable else 0.0
            conf = conf_by_product.get(product, 0.0)
            req = req_by_product.get(product, 0.0)
            free_after_conf = on_hand - conf
            free_after_all = free_after_conf - req

            if not stockable:
                status, shortfall = "na", 0.0
            elif need <= free_after_all + 1e-6:
                status, shortfall = "ok", 0.0
            elif need <= free_after_conf + 1e-6:
                # Enough vs confirmed reservations, but competing unconfirmed
                # requests could take the remaining units.
                status, shortfall = "risk", 0.0
            else:
                status, shortfall = "short", need - max(free_after_conf, 0.0)

            rows.append({
                "product": product,
                "need": need,
                "on_hand": on_hand,
                "confirmed": conf,
                "requested": req,
                "status": status,
                "shortfall": shortfall,
                "stockable": stockable,
            })
        return rows

    # ------------------------------------------------------------------
    # Message building
    # ------------------------------------------------------------------
    def _rental_availability_message_html(self):
        self.ensure_one()
        rows = self._rental_availability_rows()

        start_d = fields.Datetime.to_datetime(self.rental_start_date).date()
        end_d = fields.Datetime.to_datetime(self.rental_return_date).date()
        today = fields.Date.context_today(self)
        duration = (end_d - start_d).days
        days_to_start = (start_d - today).days

        # Overall verdict from the worst component status.
        statuses = [r["status"] for r in rows]
        if any(s == "short" for s in statuses):
            v_color, v_label = "#b00020", "Short — some equipment unavailable"
        elif any(s == "risk" for s in statuses):
            v_color, v_label = "#b26a00", "At risk — competing requests"
        elif rows:
            v_color, v_label = "#0a7d33", "Available"
        else:
            v_color, v_label = "#555555", "No stockable components to check"

        # Shipping / lead-time note.
        if days_to_start < 0:
            ship_note = "Requested start date is in the past."
        elif days_to_start < SHIPPING_DAYS_MAX:
            ship_note = ("Start is in %d day(s) — within the average shipping window "
                         "(%d–%d days). Rush shipping likely required." % (
                             days_to_start, SHIPPING_DAYS_MIN, SHIPPING_DAYS_MAX))
        else:
            ship_note = ("Start is in %d day(s) — enough lead time for standard "
                         "shipping (%d–%d days)." % (
                             days_to_start, SHIPPING_DAYS_MIN, SHIPPING_DAYS_MAX))

        th = ('style="text-align:left;padding:3px 8px;border-bottom:1px solid #ccc;'
              'font-size:11px;color:#555;text-transform:uppercase;letter-spacing:.3px;"')
        thr = th.replace("text-align:left", "text-align:right")
        parts = []
        parts.append(
            '<div style="font-size:13px;line-height:1.5;">'
            '<div style="margin-bottom:6px;">'
            '<b>📅 Rental dates requested by the customer</b><br/>'
            '<span style="color:#333;">%s → %s (%d day(s))</span>'
            '</div>'
            '<div style="margin-bottom:8px;">'
            'Availability: <b style="color:%s;">%s</b>'
            '</div>' % (
                start_d.strftime("%b %d, %Y"), end_d.strftime("%b %d, %Y"),
                duration, v_color, html_escape(v_label),
            )
        )

        parts.append(
            '<table style="border-collapse:collapse;font-size:12px;width:100%;max-width:640px;">'
            '<tr>'
            '<th %s>Component (shipped)</th>'
            '<th %s>Need</th><th %s>In stock</th>'
            '<th %s>Confirmed</th><th %s>Requested</th>'
            '<th %s>Status</th>'
            '</tr>' % (th, thr, thr, thr, thr, th)
        )
        td = 'style="padding:3px 8px;border-bottom:1px solid #eee;"'
        tdr = 'style="padding:3px 8px;border-bottom:1px solid #eee;text-align:right;"'
        for r in rows:
            color, label = _STATUS_STYLE[r["status"]]
            status_txt = label
            if r["status"] == "short" and r["shortfall"]:
                status_txt = "%s %s" % (label, _fmt_qty(r["shortfall"]))
            parts.append(
                '<tr>'
                '<td %s>%s</td>'
                '<td %s>%s</td><td %s>%s</td>'
                '<td %s>%s</td><td %s>%s</td>'
                '<td style="padding:3px 8px;border-bottom:1px solid #eee;color:%s;'
                'font-weight:600;white-space:nowrap;">%s</td>'
                '</tr>' % (
                    td, html_escape(r["product"].display_name),
                    tdr, _fmt_qty(r["need"]),
                    tdr, (_fmt_qty(r["on_hand"]) if r["stockable"] else "—"),
                    tdr, _fmt_qty(r["confirmed"]),
                    tdr, _fmt_qty(r["requested"]),
                    color, html_escape(status_txt),
                )
            )
        parts.append('</table>')

        parts.append(
            '<div style="margin-top:8px;font-size:12px;color:#444;">'
            '<div>🚚 %s</div>'
            '<div style="color:#777;margin-top:4px;">'
            '"Confirmed" = units committed to overlapping confirmed rentals; '
            '"Requested" = units wanted by other unconfirmed quotes for an '
            'overlapping window (incl. a %d-day shipping buffer each side). '
            'Figures are a point-in-time estimate — verify before promising.'
            '</div></div>'
            '</div>' % (html_escape(ship_note), SHIPPING_DAYS_MAX)
        )

        return Markup("".join(parts))

    def _notify_rental_dates_requested(self):
        """Post the salesperson-tagged availability note and pin a to-do."""
        self.ensure_one()
        body = self._rental_availability_message_html()
        salesperson = self.user_id
        author = self.env.ref("base.user_root").partner_id
        partner_ids = salesperson.partner_id.ids if (salesperson and salesperson.partner_id) else []

        self.message_post(
            body=body,
            subject=_("Rental dates requested by customer"),
            message_type="comment",
            subtype_xmlid="mail.mt_note",
            author_id=author.id,
            partner_ids=partner_ids,
        )

        # A to-do activity keeps this pinned at the top of the chatter until the
        # salesperson has checked it, and notifies them it's their action.
        if salesperson:
            try:
                self.activity_schedule(
                    "mail.mail_activity_data_todo",
                    summary=_("Customer requested rental dates — verify availability"),
                    note=Markup("<p>%s</p>") % _(
                        "The customer formally requested these rental dates from the "
                        "quote portal. See the availability breakdown in the logged note."
                    ),
                    user_id=salesperson.id,
                )
            except Exception:
                _logger.exception("Could not schedule rental-dates activity for order %s", self.id)
        return True
