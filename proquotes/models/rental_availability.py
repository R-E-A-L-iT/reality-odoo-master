# -*- coding: utf-8 -*-
"""Rental date-request + availability + salesperson response.

Portal flow:
  * Customer presses "Request dates" -> a pending request is recorded, an
    internal salesperson-tagged availability note is posted, and a to-do is
    pinned on the chatter. The button stays "Dates requested" across reloads.
  * If the customer changes the dates while a request is pending, the button
    becomes "Update request"; pressing it refreshes the pending request and
    re-runs the availability analysis.
  * The salesperson responds (available / overlapping-book-first / unavailable)
    from the order form. The response is emailed to the customer and shown,
    nicely formatted, on the quote portal. Once answered, the button is
    pressable again.

Rental quote lines are often phantom-BOM kits; what actually ships (and must be
in stock) are the kit components. Availability is computed against the exploded
components, mirroring `_build_rental_move_vals`.
"""

import logging
from collections import defaultdict
from datetime import timedelta

from markupsafe import Markup

from odoo import _, api, fields, models
from odoo.tools import html_escape

_logger = logging.getLogger(__name__)

# Average shipping time each way, in days.
SHIPPING_DAYS_MIN = 3
SHIPPING_DAYS_MAX = 4

# Theme-agnostic accent colours (readable on both light and dark chatter).
_C_OK = "#2ba15a"
_C_RISK = "#cf8412"
_C_SHORT = "#e0555f"
_C_MUTED = "#8a8a8a"

_STATUS_STYLE = {
    "ok": (_C_OK, "✔ OK"),
    "risk": (_C_RISK, "⚠ Tight"),
    "short": (_C_SHORT, "✖ Short"),
    "na": (_C_MUTED, "— n/a"),
}

# Customer-facing response copy, keyed by (response_type, lang-prefix).
# Each entry: (email subject, card title, body with {start}/{end} placeholders).
_RESPONSE_TEXTS = {
    "available": {
        "accent": _C_OK,
        "tint": "rgba(43,161,90,0.12)",
        "en": (
            "Your rental dates are available",
            "Dates available",
            "Good news! The rental dates you requested (<b>{start} → {end}</b>) "
            "are available. You can go ahead and confirm your order to reserve "
            "the equipment for these dates.",
        ),
        "fr": (
            "Vos dates de location sont disponibles",
            "Dates disponibles",
            "Bonne nouvelle! Les dates de location demandées (<b>{start} → {end}</b>) "
            "sont disponibles. Vous pouvez confirmer votre commande pour réserver "
            "l'équipement pour ces dates.",
        ),
        "es": (
            "Sus fechas de alquiler están disponibles",
            "Fechas disponibles",
            "¡Buenas noticias! Las fechas de alquiler solicitadas (<b>{start} → {end}</b>) "
            "están disponibles. Puede confirmar su pedido para reservar el equipo "
            "para estas fechas.",
        ),
    },
    "overlap": {
        "accent": _C_RISK,
        "tint": "rgba(207,132,18,0.14)",
        "en": (
            "Your requested rental dates — please book soon",
            "Book soon to secure these dates",
            "The rental dates you requested (<b>{start} → {end}</b>) are currently "
            "also being requested by other customers. Availability isn't guaranteed "
            "until an order is confirmed — we recommend confirming your order as soon "
            "as possible, as equipment is reserved on a first-confirmed basis.",
        ),
        "fr": (
            "Vos dates de location demandées — à réserver rapidement",
            "Réservez rapidement pour garantir ces dates",
            "Les dates de location demandées (<b>{start} → {end}</b>) sont "
            "actuellement aussi demandées par d'autres clients. La disponibilité "
            "n'est pas garantie tant qu'une commande n'est pas confirmée — nous vous "
            "recommandons de confirmer votre commande dès que possible, l'équipement "
            "étant réservé selon le principe du premier confirmé.",
        ),
        "es": (
            "Sus fechas de alquiler solicitadas — reserve pronto",
            "Reserve pronto para asegurar estas fechas",
            "Las fechas de alquiler solicitadas (<b>{start} → {end}</b>) también "
            "están siendo solicitadas por otros clientes. La disponibilidad no está "
            "garantizada hasta que se confirme un pedido; le recomendamos confirmar "
            "su pedido lo antes posible, ya que el equipo se reserva por orden de "
            "confirmación.",
        ),
    },
    "unavailable": {
        "accent": _C_SHORT,
        "tint": "rgba(224,85,95,0.12)",
        "en": (
            "Your requested rental dates are unavailable",
            "Dates unavailable",
            "Unfortunately, the rental dates you requested (<b>{start} → {end}</b>) "
            "are not available. Please choose different dates and submit a new "
            "request, and we'll be happy to check availability again.",
        ),
        "fr": (
            "Vos dates de location demandées ne sont pas disponibles",
            "Dates non disponibles",
            "Malheureusement, les dates de location demandées (<b>{start} → {end}</b>) "
            "ne sont pas disponibles. Veuillez choisir d'autres dates et soumettre une "
            "nouvelle demande; nous serons heureux de vérifier à nouveau la disponibilité.",
        ),
        "es": (
            "Sus fechas de alquiler solicitadas no están disponibles",
            "Fechas no disponibles",
            "Lamentablemente, las fechas de alquiler solicitadas (<b>{start} → {end}</b>) "
            "no están disponibles. Elija otras fechas y envíe una nueva solicitud; "
            "con gusto verificaremos la disponibilidad nuevamente.",
        ),
    },
}


def _fmt_qty(value):
    value = value or 0.0
    return str(int(value)) if float(value).is_integer() else ("%.2f" % value)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ---- request / response state (persisted) ----
    rental_request_state = fields.Selection(
        [("none", "None"), ("pending", "Pending"), ("answered", "Answered")],
        string="Rental Date Request",
        default="none",
        copy=False,
    )
    rental_requested_start = fields.Datetime(string="Requested Rental Start", copy=False)
    rental_requested_end = fields.Datetime(string="Requested Rental End", copy=False)
    rental_request_response = fields.Selection(
        [("available", "Available"),
         ("overlap", "Overlapping — book first"),
         ("unavailable", "Unavailable")],
        string="Rental Date Response",
        copy=False,
    )
    rental_request_response_date = fields.Datetime(string="Response Sent On", copy=False)
    rental_request_response_html = fields.Html(
        string="Rental Date Response (shown to customer)", copy=False, sanitize=False,
    )
    rental_request_activity_id = fields.Many2one(
        "mail.activity", string="Rental Request To-Do", copy=False, ondelete="set null",
    )
    rental_request_note_id = fields.Many2one(
        "mail.message", string="Rental Request Availability Note", copy=False,
        ondelete="set null",
        help="The last availability note posted for a date request; deleted and "
             "replaced when a new request/update comes in, to avoid clutter.",
    )

    # ------------------------------------------------------------------
    # Requirements (real shipped products, phantom-BOM kits exploded)
    # ------------------------------------------------------------------
    def _rental_component_requirements(self):
        """Return {product.product: qty} of the actual products that ship for
        this rental — kits exploded into components, per `_build_rental_move_vals`."""
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
        shipping buffer each side). Returns (confirmed, requested)."""
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
                status, shortfall = "risk", 0.0
            else:
                status, shortfall = "short", need - max(free_after_conf, 0.0)

            rows.append({
                "product": product, "need": need, "on_hand": on_hand,
                "confirmed": conf, "requested": req,
                "status": status, "shortfall": shortfall, "stockable": stockable,
            })
        return rows

    # ------------------------------------------------------------------
    # Availability note (internal, salesperson-tagged)
    # ------------------------------------------------------------------
    def _rental_availability_message_html(self, is_update=False):
        self.ensure_one()
        rows = self._rental_availability_rows()

        start_d = fields.Datetime.to_datetime(self.rental_start_date).date()
        end_d = fields.Datetime.to_datetime(self.rental_return_date).date()
        today = fields.Date.context_today(self)
        duration = (end_d - start_d).days
        days_to_start = (start_d - today).days

        statuses = [r["status"] for r in rows]
        if any(s == "short" for s in statuses):
            v_color, v_label = _C_SHORT, "Short — some equipment unavailable"
        elif any(s == "risk" for s in statuses):
            v_color, v_label = _C_RISK, "At risk — competing requests"
        elif rows:
            v_color, v_label = _C_OK, "Available"
        else:
            v_color, v_label = _C_MUTED, "No stockable components to check"

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

        th_base = ("padding:4px 10px;border-bottom:1px solid rgba(128,128,128,0.45);"
                   "font-size:11px;opacity:0.75;text-transform:uppercase;"
                   "letter-spacing:.3px;white-space:nowrap;")
        th_l = 'style="%stext-align:left;"' % th_base
        th_r = 'style="%stext-align:right;"' % th_base
        td = 'style="padding:4px 10px;border-bottom:1px solid rgba(128,128,128,0.2);"'
        td_r = ('style="padding:4px 10px;border-bottom:1px solid rgba(128,128,128,0.2);'
                'text-align:right;white-space:nowrap;"')

        parts = []
        title = "📅 Rental dates requested by the customer"
        if is_update:
            title = "🔁 Rental date request updated by the customer"
        parts.append(
            '<div style="font-size:13px;line-height:1.5;">'
            '<div style="margin-bottom:6px;"><b>%s</b><br/>'
            '<span style="opacity:0.85;">%s → %s (%d day(s))</span></div>'
            '<div style="margin-bottom:8px;">Availability: '
            '<b style="color:%s;">%s</b></div>' % (
                title, start_d.strftime("%b %d, %Y"), end_d.strftime("%b %d, %Y"),
                duration, v_color, html_escape(v_label))
        )

        parts.append(
            '<table style="border-collapse:collapse;font-size:12px;width:100%%;max-width:680px;">'
            '<tr><th %s>Component (shipped)</th><th %s>Need</th><th %s>In stock</th>'
            '<th %s>Confirmed</th><th %s>Requested</th><th %s>Status</th></tr>' % (
                th_l, th_r, th_r, th_r, th_r, th_l)
        )
        for r in rows:
            color, label = _STATUS_STYLE[r["status"]]
            status_txt = label
            if r["status"] == "short" and r["shortfall"]:
                status_txt = "%s %s" % (label, _fmt_qty(r["shortfall"]))
            parts.append(
                '<tr><td %s>%s</td><td %s>%s</td><td %s>%s</td>'
                '<td %s>%s</td><td %s>%s</td>'
                '<td style="padding:4px 10px;border-bottom:1px solid rgba(128,128,128,0.2);'
                'color:%s;font-weight:600;white-space:nowrap;">%s</td></tr>' % (
                    td, html_escape(r["product"].display_name),
                    td_r, _fmt_qty(r["need"]),
                    td_r, (_fmt_qty(r["on_hand"]) if r["stockable"] else "—"),
                    td_r, _fmt_qty(r["confirmed"]),
                    td_r, _fmt_qty(r["requested"]),
                    color, html_escape(status_txt))
            )
        parts.append('</table>')

        parts.append(
            '<div style="margin-top:8px;font-size:12px;">'
            '<div>🚚 %s</div>'
            '<div style="opacity:0.65;margin-top:4px;">'
            '"Confirmed" = units committed to overlapping confirmed rentals; '
            '"Requested" = units wanted by other unconfirmed quotes for an overlapping '
            'window (incl. a %d-day shipping buffer each side). Figures are a '
            'point-in-time estimate — verify before promising.</div></div></div>' % (
                html_escape(ship_note), SHIPPING_DAYS_MAX)
        )
        return Markup("".join(parts))

    def _post_rental_availability_note(self, is_update=False):
        self.ensure_one()
        # Replace the previous availability note so they don't pile up.
        if self.rental_request_note_id:
            self.rental_request_note_id.sudo().unlink()

        body = self._rental_availability_message_html(is_update=is_update)
        salesperson = self.user_id
        author = self.env.ref("base.user_root").partner_id
        partner_ids = salesperson.partner_id.ids if (salesperson and salesperson.partner_id) else []
        subject = (_("Rental date request updated by customer") if is_update
                   else _("Rental dates requested by customer"))
        message = self.message_post(
            body=body, subject=subject, message_type="comment",
            subtype_xmlid="mail.mt_note", author_id=author.id, partner_ids=partner_ids,
        )
        self.rental_request_note_id = message.id

    def _rental_request_refresh_activity(self, is_update=False):
        """(Re)create the pinned to-do for the salesperson."""
        self.ensure_one()
        if self.rental_request_activity_id:
            self.rental_request_activity_id.unlink()
        salesperson = self.user_id
        if not salesperson:
            return
        summary = (_("Customer UPDATED requested rental dates — re-check availability")
                   if is_update else
                   _("Customer requested rental dates — verify availability"))
        try:
            act = self.activity_schedule(
                "mail.mail_activity_data_todo", summary=summary,
                note=Markup("<p>%s</p>") % _(
                    "See the availability breakdown in the logged note, then respond "
                    "to the customer with the \"Respond to Date Request\" button."),
                user_id=salesperson.id,
            )
            self.rental_request_activity_id = act.id
        except Exception:
            _logger.exception("Could not schedule rental-dates activity for order %s", self.id)

    # ------------------------------------------------------------------
    # Portal-triggered request / update
    # ------------------------------------------------------------------
    def _register_rental_dates_request(self):
        """New request: mark pending, clear any prior response, post note + to-do."""
        self.ensure_one()
        self.write({
            "rental_request_state": "pending",
            "rental_requested_start": self.rental_start_date,
            "rental_requested_end": self.rental_return_date,
            "rental_request_response": False,
            "rental_request_response_html": False,
            "rental_request_response_date": False,
        })
        self._post_rental_availability_note(is_update=False)
        self._rental_request_refresh_activity(is_update=False)
        return True

    def _update_rental_dates_request(self):
        """Customer changed the dates on a still-pending request."""
        self.ensure_one()
        self.write({
            "rental_requested_start": self.rental_start_date,
            "rental_requested_end": self.rental_return_date,
        })
        self._post_rental_availability_note(is_update=True)
        self._rental_request_refresh_activity(is_update=True)
        return True

    def _handle_rental_dates_request(self):
        """Entry point from the portal button: update if pending, else register."""
        self.ensure_one()
        if self.rental_request_state == "pending":
            return self._update_rental_dates_request()
        return self._register_rental_dates_request()

    # ------------------------------------------------------------------
    # Salesperson response
    # ------------------------------------------------------------------
    def _rental_response_content(self, response_type, lang=None):
        """Return (subject, response_html) for the given response type/language."""
        self.ensure_one()
        cfg = _RESPONSE_TEXTS[response_type]
        key = "fr" if (lang or "").startswith("fr") else "es" if (lang or "").startswith("es") else "en"
        subject, card_title, body_tmpl = cfg[key]

        start = self.rental_requested_start or self.rental_start_date
        end = self.rental_requested_end or self.rental_return_date
        ds = fields.Datetime.to_datetime(start).strftime("%b %d, %Y") if start else "?"
        de = fields.Datetime.to_datetime(end).strftime("%b %d, %Y") if end else "?"
        body = body_tmpl.format(start=ds, end=de)

        html = Markup(
            '<div style="border-left:4px solid %s;background:%s;padding:10px 14px;'
            'border-radius:6px;font-size:13px;line-height:1.5;">'
            '<div style="font-weight:700;color:%s;margin-bottom:4px;">%s</div>'
            '<div>%s</div></div>' % (
                cfg["accent"], cfg["tint"], cfg["accent"],
                html_escape(card_title), body)
        )
        return subject, html

    def action_apply_rental_response(self, response_type):
        """Record + email the salesperson's response to the customer."""
        self.ensure_one()
        if response_type not in _RESPONSE_TEXTS:
            return False
        customer = self.partner_id
        lang = (customer.lang if customer else False) or self.env.user.lang or "en_US"
        subject, html = self._rental_response_content(response_type, lang)

        self.write({
            "rental_request_state": "answered",
            "rental_request_response": response_type,
            "rental_request_response_date": fields.Datetime.now(),
            "rental_request_response_html": html,
        })

        # Email + log to the customer (comment subtype notifies the recipient).
        self.message_post(
            body=html, subject=subject, message_type="comment",
            subtype_xmlid="mail.mt_comment",
            partner_ids=customer.ids if customer else [],
        )

        # Close the pinned to-do now that it's been answered.
        if self.rental_request_activity_id:
            try:
                self.rental_request_activity_id.action_feedback(
                    feedback=_("Responded to the customer: %s") % dict(
                        self._fields["rental_request_response"].selection).get(response_type, response_type)
                )
            except Exception:
                self.rental_request_activity_id.unlink()
        return True

    def action_open_rental_response_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Respond to Rental Date Request"),
            "res_model": "rental.date.response.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }


class RentalDateResponseWizard(models.TransientModel):
    _name = "rental.date.response.wizard"
    _description = "Respond to Rental Date Request"

    order_id = fields.Many2one("sale.order", string="Order", required=True, readonly=True)
    response_type = fields.Selection(
        [("available", "The requested dates are available"),
         ("overlap", "Overlapping requests — customer must book first to secure"),
         ("unavailable", "The requested dates are unavailable")],
        string="Response", required=True, default="available",
    )
    preview_html = fields.Html(string="Preview (as the customer will see it)",
                               compute="_compute_preview", sanitize=False)

    @api.depends("response_type", "order_id")
    def _compute_preview(self):
        for wiz in self:
            if wiz.order_id and wiz.response_type:
                lang = (wiz.order_id.partner_id.lang if wiz.order_id.partner_id else False) \
                    or self.env.user.lang or "en_US"
                _subject, html = wiz.order_id._rental_response_content(wiz.response_type, lang)
                wiz.preview_html = html
            else:
                wiz.preview_html = False

    def action_send(self):
        self.ensure_one()
        self.order_id.action_apply_rental_response(self.response_type)
        return {"type": "ir.actions.act_window_close"}
