# -*- coding: utf-8 -*-

import logging
from datetime import timedelta

from markupsafe import Markup, escape

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.misc import formatLang

from .constants import (
    PARTNER_NAME,
    RENTAL_DURATION_DAYS,
    TAG_LABEL,
    TAG_REF,
    TEMPLATE_RENTAL_BLANK,
    TEMPLATE_RENTAL_RTC360,
    TEMPLATE_RENEWAL_AUTO,
    TEMPLATE_SALES_BLANK,
    TEMPLATE_SALES_RTC360,
)

_logger = logging.getLogger(__name__)


class ProUpgradeTestRun(models.Model):
    _name = "pro.upgrade.test.run"
    _description = "Enginelly Upgrade Test Run"
    _inherit = ["mail.thread"]
    _order = "create_date desc, id desc"

    name = fields.Char(required=True, default=lambda self: _("Enginelly test run"), tracking=True)
    state = fields.Selection(
        [
            ("running", "Running"),
            ("done", "Done"),
            ("partial", "Partial"),
            ("failed", "Failed"),
        ],
        default="running",
        required=True,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )
    currency_id = fields.Many2one(
        related="company_id.currency_id",
        store=True,
        readonly=True,
    )
    report_html = fields.Html(string="Run report", sanitize=True, readonly=True)
    line_ids = fields.One2many(
        "pro.upgrade.test.run.line",
        "run_id",
        string="Steps",
        copy=False,
    )
    sale_order_ids = fields.Many2many(
        "sale.order",
        "pro_upgrade_test_run_sale_order_rel",
        "run_id",
        "order_id",
        string="Created orders",
        copy=False,
    )
    order_count = fields.Integer(compute="_compute_order_count")
    pass_count = fields.Integer(compute="_compute_status_counts")
    fail_count = fields.Integer(compute="_compute_status_counts")
    skip_count = fields.Integer(compute="_compute_status_counts")

    @api.depends("sale_order_ids")
    def _compute_order_count(self):
        for run in self:
            run.order_count = len(run.sale_order_ids)

    @api.depends("line_ids.status")
    def _compute_status_counts(self):
        for run in self:
            run.pass_count = len(run.line_ids.filtered(lambda l: l.status == "pass"))
            run.fail_count = len(run.line_ids.filtered(lambda l: l.status == "fail"))
            run.skip_count = len(run.line_ids.filtered(lambda l: l.status == "skip"))

    def action_view_orders(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": _("Enginelly test orders"),
            "res_model": "sale.order",
            "view_mode": "list,form",
            "domain": [("id", "in", self.sale_order_ids.ids)],
            "target": "current",
        }

    def action_rebuild_new_run(self):
        """Create a fresh run (does not reuse this record's lines)."""
        run = self._rebuild_suite()
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": run.id,
            "view_mode": "form",
            "target": "current",
        }

    @api.model
    def _rebuild_suite(self):
        run = self.create(
            {
                "name": _("Enginelly test run %(stamp)s", stamp=fields.Datetime.now()),
                "state": "running",
                "company_id": self.env.company.id,
            }
        )
        run._execute_suite()
        return run

    def _execute_suite(self):
        self.ensure_one()
        try:
            self._step_cancel_prior()
            partner, pricelist, blocking = self._resolve_prerequisites()
            if blocking:
                for message in blocking:
                    self._add_line(
                        "prerequisites",
                        _("Prerequisites"),
                        "fail",
                        error=message,
                    )
            else:
                self._step_sales_blank(partner, pricelist)
                self._step_sales_rtc360(partner, pricelist)
                self._step_minimal_sale(partner, pricelist)
                self._step_rental_blank(partner, pricelist)
                self._step_rental_process(partner, pricelist)
                self._step_renewal_auto(partner, pricelist)
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: suite aborted")
            self._add_line(
                "fatal",
                _("Suite aborted"),
                "fail",
                error=str(exc),
            )
        self._finalize()

    # ------------------------------------------------------------------
    # Report
    # ------------------------------------------------------------------

    def _finalize(self):
        self.ensure_one()
        fails = self.line_ids.filtered(lambda l: l.status == "fail")
        passes = self.line_ids.filtered(lambda l: l.status == "pass")
        if fails and passes:
            state = "partial"
        elif fails:
            state = "failed"
        else:
            state = "done"
        report = self._render_report_html()
        self.write(
            {
                "state": state,
                "report_html": report,
            }
        )
        self.message_post(
            body=Markup(report or "<p>No steps recorded.</p>"),
            subject=_("Enginelly test suite rebuild"),
        )

    def _render_report_html(self):
        self.ensure_one()
        rows = []
        for line in self.line_ids.sorted("sequence"):
            status = (line.status or "").upper()
            if line.status == "pass":
                badge = '<span class="badge text-bg-success">PASS</span>'
            elif line.status == "fail":
                badge = '<span class="badge text-bg-danger">FAIL</span>'
            else:
                badge = '<span class="badge text-bg-secondary">SKIP</span>'
            doc = escape(line.document_name or "—")
            if line.res_model and line.res_id:
                doc = Markup("%s <small>(%s,%s)</small>") % (
                    line.document_name or "—",
                    line.res_model,
                    line.res_id,
                )
            amount = ""
            if line.amount_total:
                amount = escape(
                    formatLang(self.env, line.amount_total, currency_obj=self.env.company.currency_id)
                )
            detail = escape(line.error_message or line.note or "")
            rows.append(
                Markup(
                    "<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>"
                )
                % (line.name or line.step_code, Markup(badge), doc, amount, detail)
            )
        body = Markup("").join(rows)
        summary = Markup(
            "<p><strong>%s</strong> — PASS %s / FAIL %s / SKIP %s</p>"
        ) % (self.name, self.pass_count, self.fail_count, self.skip_count)
        table = Markup(
            "<table class='table table-sm table-hover'>"
            "<thead><tr>"
            "<th>Step</th><th>Status</th><th>Document</th><th>Amount</th><th>Notes</th>"
            "</tr></thead><tbody>%s</tbody></table>"
        ) % body
        return summary + table

    def _add_line(
        self,
        step_code,
        name,
        status,
        *,
        record=None,
        error=None,
        note=None,
        amount_total=None,
    ):
        self.ensure_one()
        vals = {
            "run_id": self.id,
            "sequence": max(self.line_ids.mapped("sequence") or [0]) + 1,
            "step_code": step_code,
            "name": name,
            "status": status,
            "error_message": error or False,
            "note": note or False,
        }
        if record:
            vals.update(
                {
                    "res_model": record._name,
                    "res_id": record.id,
                    "document_name": record.display_name,
                }
            )
            if amount_total is None and "amount_total" in record._fields:
                amount_total = record.amount_total
            if record._name == "sale.order" and record not in self.sale_order_ids:
                self.sale_order_ids = [(4, record.id)]
        if amount_total is not None:
            vals["amount_total"] = amount_total
        return self.env["pro.upgrade.test.run.line"].create(vals)

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def _resolve_prerequisites(self):
        errors = []
        partner = self._find_partner()
        if not partner:
            errors.append(
                _('Partner "%s" was not found. Create that company partner on OriginCopy and re-run.')
                % PARTNER_NAME
            )
            return self.env["res.partner"], self.env["product.pricelist"], errors
        pricelist = self._find_pricelist(partner)
        if not pricelist:
            errors.append(
                _(
                    "No usable pricelist found (proquotes excludes names containing "
                    "'Default'). Assign a CAD/USD pricelist on the test partner or company."
                )
            )
        return partner, pricelist, errors

    def _find_partner(self):
        Partner = self.env["res.partner"]
        partner = Partner.search(
            [("name", "=", PARTNER_NAME), ("is_company", "=", True)],
            limit=1,
        )
        if partner:
            return partner
        return Partner.search([("name", "ilike", PARTNER_NAME)], limit=1)

    def _find_pricelist(self, partner):
        Pricelist = self.env["product.pricelist"]
        candidate = partner.property_product_pricelist
        if candidate and "default" not in (candidate.name or "").lower():
            return candidate
        domain = [("name", "not ilike", "Default")]
        if "company_id" in Pricelist._fields:
            domain = [
                ("name", "not ilike", "Default"),
                "|",
                ("company_id", "=", False),
                ("company_id", "=", self.env.company.id),
            ]
        return Pricelist.search(domain, limit=1)

    def _find_template(self, names):
        Template = self.env["sale.order.template"]
        for name in names:
            template = Template.search([("name", "=", name)], limit=1)
            if template:
                return template
        return Template.search([("name", "ilike", names[0])], limit=1)

    def _find_payment_term(self):
        return self.env["account.payment.term"].search(
            [("name", "=", "Immediate Payment")],
            limit=1,
        )

    def _find_simple_sale_products(self, limit=2):
        Product = self.env["product.product"]
        common = [("sale_ok", "=", True), ("active", "=", True)]
        found = Product.browse()
        found |= self._filter_non_kit(Product.search(common + [("type", "=", "service")], limit=limit * 3), limit)
        if len(found) >= limit:
            return found[:limit]
        if "is_storable" in Product._fields:
            found |= self._filter_non_kit(
                Product.search(
                    common + [("is_storable", "=", False), ("id", "not in", found.ids)],
                    limit=limit * 3,
                ),
                limit - len(found),
            )
        if len(found) >= limit:
            return found[:limit]
        found |= self._filter_non_kit(
            Product.search(common + [("id", "not in", found.ids)], limit=limit * 3),
            limit - len(found),
        )
        return found[:limit]

    def _filter_non_kit(self, products, limit):
        kept = self.env["product.product"]
        for product in products:
            if self._product_is_kit(product):
                continue
            kept |= product
            if len(kept) >= limit:
                break
        return kept

    def _product_is_kit(self, product):
        if "mrp.bom" not in self.env:
            return False
        return bool(
            self.env["mrp.bom"].sudo().search(
                [
                    ("product_tmpl_id", "=", product.product_tmpl_id.id),
                    ("type", "=", "phantom"),
                ],
                limit=1,
            )
        )

    def _find_rentable_product(self):
        Product = self.env["product.product"]
        if "rent_ok" not in Product._fields:
            return Product.browse()
        products = Product.search(
            [("rent_ok", "=", True), ("sale_ok", "=", True), ("active", "=", True)],
            limit=8,
        )
        non_kit = self._filter_non_kit(products, 1)
        return non_kit[:1] or products[:1]

    # ------------------------------------------------------------------
    # Order helpers
    # ------------------------------------------------------------------

    def _order_ref(self):
        return "%s %s" % (TAG_REF, TAG_LABEL)

    def _order_note_text(self):
        return (
            "%s %s — rebuilt by pro_upgrade_testkit. "
            "Do not treat as a real customer order."
        ) % (TAG_REF, TAG_LABEL)

    def _base_order_vals(self, partner, pricelist, extra=None):
        vals = {
            "partner_id": partner.id,
            "partner_invoice_id": partner.id,
            "partner_shipping_id": partner.id,
            "company_id": self.env.company.id,
            "pricelist_id": pricelist.id,
            "client_order_ref": self._order_ref(),
            "user_id": self.env.user.id,
        }
        payment_term = self._find_payment_term()
        if payment_term:
            vals["payment_term_id"] = payment_term.id
        if extra:
            vals.update(extra)
        return vals

    def _write_note(self, order):
        if "note" not in order._fields:
            return
        text = self._order_note_text()
        if order._fields["note"].type == "html":
            order.note = Markup("<p>%s</p>") % text
        else:
            order.note = text

    def _create_quote(self, partner, pricelist, extra_vals=None, template=None, context=None, product_ids=None):
        ctx = dict(context or {})
        SaleOrder = self.env["sale.order"].with_context(**ctx) if ctx else self.env["sale.order"]
        vals = self._base_order_vals(partner, pricelist, extra=extra_vals)
        if template:
            vals["sale_order_template_id"] = template.id
        order = SaleOrder.create(vals)
        self._write_note(order)
        if template:
            self._apply_template(order, template)
        if product_ids:
            self._add_products(order, product_ids, context=ctx)
        order.message_post(
            body=Markup("<p>%s</p>")
            % (_("%s document created by pro_upgrade_testkit.") % TAG_LABEL)
        )
        self.sale_order_ids = [(4, order.id)]
        return order

    def _apply_template(self, order, template):
        if not template:
            return
        if not order.sale_order_template_id:
            order.sale_order_template_id = template.id
        applied = False
        if hasattr(order, "_onchange_sale_order_template_id"):
            try:
                order._onchange_sale_order_template_id()
                applied = True
            except Exception:
                _logger.exception(
                    "pro_upgrade_testkit: _onchange_sale_order_template_id failed for %s",
                    template.name,
                )
        if hasattr(order, "_onchange_sale_order_template_id_set_header_footer"):
            try:
                order._onchange_sale_order_template_id_set_header_footer()
            except Exception:
                _logger.exception("pro_upgrade_testkit: header/footer onchange failed")
        if applied and order.order_line:
            order.flush_recordset()
            return
        self._copy_template_lines(order, template)

    def _copy_template_lines(self, order, template):
        lines = template.sale_order_template_line_ids
        if not lines:
            return
        commands = [(5, 0, 0)]
        for tline in lines:
            vals = None
            if hasattr(tline, "_prepare_order_line_values"):
                try:
                    vals = tline._prepare_order_line_values()
                except TypeError:
                    vals = tline._prepare_order_line_values(order)
            if not vals and hasattr(template, "_prepare_sale_order_line_values"):
                vals = template._prepare_sale_order_line_values(order, tline)
            if not vals:
                vals = {
                    "display_type": tline.display_type or False,
                    "name": tline.name,
                    "product_id": tline.product_id.id if tline.product_id else False,
                    "product_uom_qty": tline.product_uom_qty if tline.product_id else 0,
                }
                if tline.product_id and "product_uom_id" in self.env["sale.order.line"]._fields:
                    uom = getattr(tline, "product_uom_id", False) or tline.product_id.uom_id
                    if uom:
                        vals["product_uom_id"] = uom.id
                for fname in ("x_single_choice", "hiddenSection", "quantityLocked", "is_optional"):
                    if fname in tline._fields and fname in self.env["sale.order.line"]._fields:
                        vals[fname] = tline[fname]
            commands.append((0, 0, vals))
        order.write({"order_line": commands})

    def _add_products(self, order, product_ids, context=None):
        ctx = dict(context or {})
        Line = self.env["sale.order.line"].with_context(**ctx) if ctx else self.env["sale.order.line"]
        for product in self.env["product.product"].browse(product_ids):
            Line.create(
                {
                    "order_id": order.id,
                    "product_id": product.id,
                    "product_uom_qty": 1,
                }
            )

    def _proquotes_selection_note(self, order):
        Line = order.order_line
        bits = []
        if "x_single_choice" in Line._fields:
            sections = Line.filtered(lambda l: l.x_single_choice)
            bits.append("%s single-choice section(s)" % len(sections))
        if "x_optional_member" in Line._fields:
            members = Line.filtered(lambda l: l.x_optional_member)
            bits.append("%s optional member line(s)" % len(members))
        elif "is_optional" in Line._fields:
            optional = Line.filtered(lambda l: l.is_optional)
            bits.append("%s optional line(s)" % len(optional))
        return "; ".join(bits) if bits else "proquotes optional/single-choice fields not present"

    # ------------------------------------------------------------------
    # Cancel prior runs
    # ------------------------------------------------------------------

    def _prior_test_orders(self):
        return self.env["sale.order"].search(
            [
                "|",
                ("client_order_ref", "ilike", TAG_REF),
                ("note", "ilike", TAG_REF),
            ]
        )

    def _cancel_sale_order(self, order):
        for invoice in order.invoice_ids.filtered(lambda m: m.state != "cancel"):
            if invoice.state == "posted":
                if getattr(invoice, "payment_state", "not_paid") in ("paid", "in_payment", "partial"):
                    raise UserError(
                        _("Invoice %s is paid/partially paid and was left untouched.")
                        % invoice.name
                    )
                invoice.button_draft()
            if invoice.state == "draft":
                invoice.button_cancel()
        pickings = order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
        for picking in pickings:
            picking.action_cancel()
        if order.state != "cancel":
            if hasattr(order, "action_cancel"):
                order.with_context(disable_cancel_warning=True).action_cancel()
            elif hasattr(order, "_action_cancel"):
                order._action_cancel()
            else:
                order.write({"state": "cancel"})

    def _step_cancel_prior(self):
        orders = self._prior_test_orders()
        cancelled = 0
        skipped = 0
        errors = []
        for order in orders:
            if order.state == "cancel":
                skipped += 1
                continue
            try:
                with self.env.cr.savepoint():
                    self._cancel_sale_order(order)
                cancelled += 1
            except Exception as exc:
                _logger.warning("pro_upgrade_testkit: could not cancel %s: %s", order.name, exc)
                errors.append("%s: %s" % (order.display_name, exc))
        note = _("Cancelled %s order(s); %s already cancelled.") % (cancelled, skipped)
        if errors:
            self._add_line(
                "cancel_prior",
                _("Cancel prior Enginelly documents"),
                "fail",
                error="%s | %s" % (note, " ; ".join(errors)),
            )
        else:
            self._add_line(
                "cancel_prior",
                _("Cancel prior Enginelly documents"),
                "pass",
                note=note,
            )

    # ------------------------------------------------------------------
    # Suite steps
    # ------------------------------------------------------------------

    def _step_sales_blank(self, partner, pricelist):
        template = self._find_template(TEMPLATE_SALES_BLANK)
        if not template:
            self._add_line(
                "sales_blank",
                _("Sales Blank quote (draft)"),
                "skip",
                error=_('Quotation template "%s" not found.') % TEMPLATE_SALES_BLANK[0],
            )
            return
        try:
            with self.env.cr.savepoint():
                order = self._create_quote(partner, pricelist, template=template)
                self._add_line(
                    "sales_blank",
                    _("Sales Blank quote (draft)"),
                    "pass",
                    record=order,
                    note=_("Left in draft."),
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: sales blank failed")
            self._add_line(
                "sales_blank",
                _("Sales Blank quote (draft)"),
                "fail",
                error=str(exc),
            )

    def _step_sales_rtc360(self, partner, pricelist):
        template = self._find_template(TEMPLATE_SALES_RTC360)
        if not template:
            self._add_line(
                "sales_rtc360",
                _("SALES - RTC360 quote (draft)"),
                "skip",
                error=_('Quotation template "%s" not found.') % TEMPLATE_SALES_RTC360[0],
            )
            return
        try:
            with self.env.cr.savepoint():
                order = self._create_quote(partner, pricelist, template=template)
                note = self._proquotes_selection_note(order)
                self._add_line(
                    "sales_rtc360",
                    _("SALES - RTC360 quote (draft)"),
                    "pass",
                    record=order,
                    note=_("Left in draft with template selection state: %s") % note,
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: sales rtc360 failed")
            self._add_line(
                "sales_rtc360",
                _("SALES - RTC360 quote (draft)"),
                "fail",
                error=str(exc),
            )

    def _step_minimal_sale(self, partner, pricelist):
        products = self._find_simple_sale_products(limit=2)
        if not products:
            self._add_line(
                "sale_minimal_confirm",
                _("Minimal sale order (confirm)"),
                "fail",
                error=_("No saleable service/non-stock product found to build a minimal order."),
            )
            return
        template = self._find_template(TEMPLATE_SALES_BLANK)
        extra_note = ""
        if not template:
            extra_note = _('Template "%s" missing; created without a quotation template. ') % TEMPLATE_SALES_BLANK[0]
        try:
            with self.env.cr.savepoint():
                order = self._create_quote(
                    partner,
                    pricelist,
                    template=template,
                    product_ids=products.ids,
                )
                order.action_confirm()
                self._add_line(
                    "sale_minimal_confirm",
                    _("Minimal sale order (confirm)"),
                    "pass",
                    record=order,
                    note=extra_note + _("Confirmed. Products: %s") % ", ".join(products.mapped("display_name")),
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: minimal confirm failed")
            self._add_line(
                "sale_minimal_confirm",
                _("Minimal sale order (confirm)"),
                "fail",
                error=str(exc),
            )
            return
        self._step_minimal_invoice(order)
        self._step_minimal_delivery(order)

    def _step_minimal_invoice(self, order):
        try:
            with self.env.cr.savepoint():
                invoices = self._create_and_post_invoices(order)
                if not invoices:
                    raise UserError(_("No invoice was created."))
                self._add_line(
                    "sale_minimal_invoice",
                    _("Minimal sale — create & post invoice"),
                    "pass",
                    record=invoices[0],
                    amount_total=sum(invoices.mapped("amount_total")),
                    note=_("Posted invoice(s): %s") % ", ".join(invoices.mapped("name")),
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: invoice failed")
            self._add_line(
                "sale_minimal_invoice",
                _("Minimal sale — create & post invoice"),
                "fail",
                error=str(exc),
            )

    def _create_and_post_invoices(self, order):
        try:
            invoices = order._create_invoices()
        except UserError as exc:
            if "nothing to invoice" in str(exc).lower():
                invoices = order._create_invoices(final=True)
            else:
                raise
        if not invoices:
            invoices = order._create_invoices(final=True)
        if "ref" in invoices._fields:
            invoices.write({"ref": self._order_ref()})
        invoices.action_post()
        return invoices

    def _step_minimal_delivery(self, order):
        pickings = order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
        if not pickings:
            self._add_line(
                "sale_minimal_delivery",
                _("Minimal sale — validate delivery"),
                "skip",
                record=order,
                note=_("No picking to validate (typical for service-only orders)."),
            )
            return
        try:
            with self.env.cr.savepoint():
                names = []
                for picking in pickings:
                    self._validate_picking(picking)
                    names.append(picking.display_name)
                self._add_line(
                    "sale_minimal_delivery",
                    _("Minimal sale — validate delivery"),
                    "pass",
                    record=pickings[0],
                    note=_("Validated: %s") % ", ".join(names),
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: delivery validate failed")
            self._add_line(
                "sale_minimal_delivery",
                _("Minimal sale — validate delivery"),
                "fail",
                error=str(exc),
            )

    def _validate_picking(self, picking):
        moves = picking.move_ids
        qty_field = "quantity" if "quantity" in moves._fields else "quantity_done"
        for move in moves:
            if not getattr(move, qty_field, 0):
                setattr(move, qty_field, move.product_uom_qty)
        result = picking.with_context(
            skip_backorder=True,
            skip_sms=True,
            skip_immediate=True,
            cancel_backorder=True,
        ).button_validate()
        if isinstance(result, dict) and result.get("res_model"):
            wizard = (
                self.env[result["res_model"]]
                .with_context(dict(result.get("context") or {}))
                .create({})
            )
            for method_name in (
                "process",
                "button_validate",
                "action_confirm",
                "process_cancel_backorder",
            ):
                if hasattr(wizard, method_name):
                    getattr(wizard, method_name)()
                    break

    def _rental_dates(self):
        start = fields.Datetime.now().replace(minute=0, second=0, microsecond=0)
        end = start + timedelta(days=RENTAL_DURATION_DAYS)
        extra = {
            "is_rental_order": True,
            "rental_start_date": start,
            "rental_return_date": end,
        }
        if "pickup_date" in self.env["sale.order"]._fields:
            extra["pickup_date"] = start
        return extra

    def _step_rental_blank(self, partner, pricelist):
        if "is_rental_order" not in self.env["sale.order"]._fields:
            self._add_line(
                "rental_blank",
                _("Rental Blank quote (draft)"),
                "skip",
                error=_("sale.order.is_rental_order is not available."),
            )
            return
        template = self._find_template(TEMPLATE_RENTAL_BLANK)
        if not template:
            self._add_line(
                "rental_blank",
                _("Rental Blank quote (draft)"),
                "skip",
                error=_('Quotation template "%s" not found.') % TEMPLATE_RENTAL_BLANK[0],
            )
            return
        try:
            with self.env.cr.savepoint():
                order = self._create_quote(
                    partner,
                    pricelist,
                    extra_vals=self._rental_dates(),
                    template=template,
                    context={"in_rental_app": True},
                )
                self._add_line(
                    "rental_blank",
                    _("Rental Blank quote (draft)"),
                    "pass",
                    record=order,
                    note=_("Left in draft with a %s-day rental window.") % RENTAL_DURATION_DAYS,
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: rental blank failed")
            self._add_line(
                "rental_blank",
                _("Rental Blank quote (draft)"),
                "fail",
                error=str(exc),
            )

    def _step_rental_process(self, partner, pricelist):
        if "is_rental_order" not in self.env["sale.order"]._fields:
            self._add_line(
                "rental_process",
                _("Rental process (confirm)"),
                "skip",
                error=_("sale.order.is_rental_order is not available."),
            )
            return
        template = self._find_template(TEMPLATE_RENTAL_RTC360)
        product = self.env["product.product"]
        source_note = ""
        if template:
            source_note = _('Applied template "%s".') % template.display_name
        else:
            product = self._find_rentable_product()
            blank = self._find_template(TEMPLATE_RENTAL_BLANK)
            template = blank
            if not product and not (blank and blank.sale_order_template_line_ids.filtered("product_id")):
                self._add_line(
                    "rental_process",
                    _("Rental process (confirm)"),
                    "skip",
                    error=_(
                        'Template "%s" not found and no rentable product (rent_ok) is available.'
                    )
                    % TEMPLATE_RENTAL_RTC360[0],
                )
                return
            source_note = _(
                'Template "%s" missing; using %s%s.'
            ) % (
                TEMPLATE_RENTAL_RTC360[0],
                blank.display_name if blank else _("no rental template"),
                (_(" + product %s") % product.display_name) if product else "",
            )
        order = self.env["sale.order"]
        try:
            with self.env.cr.savepoint():
                order = self._create_quote(
                    partner,
                    pricelist,
                    extra_vals=self._rental_dates(),
                    template=template,
                    context={"in_rental_app": True},
                    product_ids=product.ids if product else None,
                )
                order.with_context(in_rental_app=True).action_confirm()
                if hasattr(order, "_recompute_rental_prices"):
                    order._recompute_rental_prices()
                self._add_line(
                    "rental_process",
                    _("Rental process (confirm)"),
                    "pass",
                    record=order,
                    note=source_note,
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: rental confirm failed")
            self._add_line(
                "rental_process",
                _("Rental process (confirm)"),
                "fail",
                error="%s | %s" % (source_note, exc),
            )
            return
        self._step_rental_pickup(order)

    def _step_rental_pickup(self, order):
        try:
            with self.env.cr.savepoint():
                if hasattr(order, "action_open_pickup"):
                    order.action_open_pickup()
                    note = _("Called action_open_pickup.")
                    picking = order.picking_ids[:1]
                    if picking:
                        try:
                            self._validate_picking(picking)
                            note += _(" Validated picking %s.") % picking.display_name
                        except Exception as pick_exc:
                            note += _(" Pickup wizard ran; picking validate failed: %s") % pick_exc
                    self._add_line(
                        "rental_pickup",
                        _("Rental pickup / stock"),
                        "pass",
                        record=picking or order,
                        note=note,
                    )
                else:
                    pickings = order.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
                    if not pickings:
                        raise UserError(_("No action_open_pickup method and no picking to validate."))
                    self._validate_picking(pickings[0])
                    self._add_line(
                        "rental_pickup",
                        _("Rental pickup / stock"),
                        "pass",
                        record=pickings[0],
                        note=_("Validated rental picking without action_open_pickup."),
                    )
        except Exception as exc:
            _logger.warning("pro_upgrade_testkit: rental pickup failed: %s", exc)
            self._add_line(
                "rental_pickup",
                _("Rental pickup / stock"),
                "fail",
                record=order,
                error=str(exc),
            )

    def _step_renewal_auto(self, partner, pricelist):
        template = self._find_template(TEMPLATE_RENEWAL_AUTO)
        if not template:
            self._add_line(
                "renewal_auto",
                _("Renewal Auto quote (draft)"),
                "skip",
                error=_('Quotation template "%s" not found.') % TEMPLATE_RENEWAL_AUTO[0],
            )
            return
        try:
            with self.env.cr.savepoint():
                order = self._create_quote(partner, pricelist, template=template)
                self._add_line(
                    "renewal_auto",
                    _("Renewal Auto quote (draft)"),
                    "pass",
                    record=order,
                    note=_("Left in draft."),
                )
        except Exception as exc:
            _logger.exception("pro_upgrade_testkit: renewal auto failed")
            self._add_line(
                "renewal_auto",
                _("Renewal Auto quote (draft)"),
                "fail",
                error=str(exc),
            )


class ProUpgradeTestRunLine(models.Model):
    _name = "pro.upgrade.test.run.line"
    _description = "Enginelly Upgrade Test Run Line"
    _order = "sequence, id"

    run_id = fields.Many2one(
        "pro.upgrade.test.run",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    step_code = fields.Char(required=True, index=True)
    name = fields.Char(required=True)
    status = fields.Selection(
        [
            ("pass", "PASS"),
            ("fail", "FAIL"),
            ("skip", "SKIP"),
        ],
        required=True,
        default="skip",
    )
    res_model = fields.Char()
    res_id = fields.Integer()
    document_name = fields.Char()
    amount_total = fields.Monetary(currency_field="currency_id")
    currency_id = fields.Many2one(
        related="run_id.currency_id",
        store=True,
        readonly=True,
    )
    error_message = fields.Text()
    note = fields.Char()

    def action_open_document(self):
        self.ensure_one()
        if not self.res_model or not self.res_id:
            return False
        return {
            "type": "ir.actions.act_window",
            "res_model": self.res_model,
            "res_id": self.res_id,
            "view_mode": "form",
            "target": "current",
        }
