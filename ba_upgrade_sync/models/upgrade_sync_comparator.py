# -*- coding: utf-8 -*-
"""Compare the business outcome in Odoo 19 with the Odoo 17 snapshot.

Only meaningful business values are compared (customer, amounts, line count,
state after an action), not technical fields: Odoo 17 and Odoo 19 can
legitimately differ structurally.
"""
from markupsafe import Markup, escape

from odoo import api, models

AMOUNT_TOLERANCE = 0.01
# state is compared only after the event that sets it
STATE_EVENTS = {
    "sale.confirm": "sale",
    "sale.cancel": "cancel",
    "sale.sent": "sent",
    "invoice.post": "posted",
    "invoice.cancel": "cancel",
}


class UpgradeSyncComparator(models.AbstractModel):
    _name = "upgrade.sync.comparator"
    _description = "Upgrade Sync Odoo 17 / Odoo 19 Comparison"

    @api.model
    def _compare(self, event, payload, target):
        """Return (result, html) with result in match / mismatch / na."""
        snap = payload.get("record") or {}
        if not target or target._name not in ("sale.order", "account.move"):
            return "na", False
        rows = self._rows(event, snap, target)
        if not rows:
            return "na", False
        result = "match" if all(ok for (_l, _a, _b, ok) in rows) else "mismatch"
        return result, self._render(rows, result)

    @api.model
    def _rows(self, event, snap, target):
        rows = []

        def amount(label, a, b):
            rows.append((label, a, b, abs((a or 0.0) - (b or 0.0)) <= AMOUNT_TOLERANCE))

        partner_ref = snap.get("partner_id") or {}
        expected_partner = self.env["upgrade.sync.mapping"]._lookup("res.partner", partner_ref.get("id"))
        rows.append((
            "Customer", partner_ref.get("name"), target.partner_id.display_name,
            bool(expected_partner) and expected_partner == target.partner_id,
        ))
        amount("Untaxed", snap.get("amount_untaxed"), target.amount_untaxed)
        amount("Tax", snap.get("amount_tax"), target.amount_tax)
        amount("Total", snap.get("amount_total"), target.amount_total)

        if target._name == "sale.order":
            src_lines = [l for l in snap.get("lines") or []
                         if not l.get("display_type") and not l.get("x_is_rental_kit_component")
                         and not l.get("is_downpayment")]
            dst_lines = target.order_line.filtered(
                lambda l: not l.display_type and not l.x_is_rental_kit_component and not l.is_downpayment)
            rows.append(("Product lines", len(src_lines), len(dst_lines), len(src_lines) == len(dst_lines)))
            src_selected = sum(1 for l in src_lines if l.get("selected") != "false"
                               and l.get("sectionSelected") != "false" and l.get("product_uom_qty"))
            dst_selected = len(dst_lines.filtered(lambda l: l.product_uom_qty))
            rows.append(("Selected lines", src_selected, dst_selected, src_selected == dst_selected))
        else:
            src_lines = [l for l in snap.get("lines") or [] if (l.get("display_type") or "product") == "product"]
            dst_lines = target.invoice_line_ids.filtered(lambda l: l.display_type == "product")
            rows.append(("Invoice lines", len(src_lines), len(dst_lines), len(src_lines) == len(dst_lines)))

        expected_state = STATE_EVENTS.get(event.event_type)
        if expected_state:
            rows.append(("State", snap.get("state"), target.state, target.state == expected_state))
        return rows

    @api.model
    def _render(self, rows, result):
        body = Markup("").join(
            Markup("<tr class='%s'><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>") % (
                "" if ok else "table-danger", label, _fmt(a), _fmt(b), "OK" if ok else "DIFF")
            for (label, a, b, ok) in rows
        )
        return Markup(
            "<table class='table table-sm'><thead><tr><th>Check</th><th>Odoo 17</th>"
            "<th>Odoo 19</th><th></th></tr></thead><tbody>%s</tbody></table>"
            "<p><strong>Business result: %s</strong></p>"
        ) % (body, escape(result.upper()))


def _fmt(value):
    if isinstance(value, float):
        return "%.2f" % value
    return "" if value is None else value
