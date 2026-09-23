# -*- coding: utf-8 -*-
"""Business snapshots sent to Odoo 19.

A relation is never sent as a bare database id: it is sent as a *reference*
``{"model", "id", "name", "create_date", "keys": {...}}`` so the receiver can
resolve it through its mapping table, the same id (the Odoo 19 database is an
upgraded copy) checked by fingerprint, or business keys.

Extend with ``_inherit = "upgrade.sync.serializer"`` and override
``_snapshot_<model_with_underscores>`` / ``_ref_keys`` to add custom fields.
"""
from odoo import api, models


class UpgradeSyncSerializer(models.AbstractModel):
    _name = "upgrade.sync.serializer"
    _description = "Upgrade Sync Snapshot Builder (Odoo 17)"

    # ------------------------------------------------------------------
    # References
    # ------------------------------------------------------------------
    @api.model
    def _ref(self, record):
        if not record:
            return None
        record = record[:1]
        return {
            "model": record._name,
            "id": record.id,
            "name": record.display_name,
            "create_date": record.create_date and record.create_date.isoformat(),
            "keys": self._ref_keys(record),
        }

    @api.model
    def _refs(self, records):
        return [self._ref(rec) for rec in records]

    @api.model
    def _ref_keys(self, record):
        model = record._name
        if model == "res.partner":
            return {
                "email": record.email or None,
                "vat": record.vat or None,
                "ref": record.ref or None,
                "is_company": record.is_company,
                "parent_id": record.parent_id.id or None,
                "name": record.name or None,
            }
        if model in ("product.product", "product.template"):
            return {
                "default_code": record.default_code or None,
                "barcode": record.barcode or None,
                "name": record.name,
            }
        if model == "account.tax":
            return {
                "name": record.name,
                "amount": record.amount,
                "amount_type": record.amount_type,
                "type_tax_use": record.type_tax_use,
                "company": record.company_id.name,
            }
        if model == "account.journal":
            return {"code": record.code, "type": record.type, "company": record.company_id.name}
        if model == "account.account":
            return {"code": record.code, "company": record.company_id.name}
        if model == "res.users":
            return {"login": record.login}
        if model == "res.country":
            return {"code": record.code}
        if model == "res.country.state":
            return {"code": record.code, "country_code": record.country_id.code}
        if model == "res.currency":
            return {"name": record.name}
        if model == "uom.uom":
            return {"name": record.name, "category": record.category_id.name}
        if model == "product.category":
            return {"complete_name": record.complete_name}
        return {"name": record.display_name}

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------
    @api.model
    def _snapshot(self, record):
        method = getattr(self, "_snapshot_%s" % record._name.replace(".", "_"), None)
        data = method(record) if method else {}
        data.update({
            "id": record.id,
            "model": record._name,
            "create_date": record.create_date and record.create_date.isoformat(),
            "write_date": record.write_date and record.write_date.isoformat(),
        })
        return data

    @api.model
    def _snapshot_res_partner(self, p):
        return {
            "name": p.name,
            "is_company": p.is_company,
            "parent_id": self._ref(p.parent_id),
            "type": p.type,
            "email": p.email or False,
            "phone": p.phone or False,
            "mobile": p.mobile or False,
            "street": p.street or False,
            "street2": p.street2 or False,
            "city": p.city or False,
            "zip": p.zip or False,
            "state_id": self._ref(p.state_id),
            "country_id": self._ref(p.country_id),
            "vat": p.vat or False,
            "ref": p.ref or False,
            "lang": p.lang or False,
            "website": p.website or False,
            "function": p.function or False,
            "company_id": self._ref(p.company_id),
            "user_id": self._ref(p.user_id),
            "category_ids": self._refs(p.category_id),
            "property_payment_term_id": self._ref(p.property_payment_term_id),
            "property_product_pricelist": self._ref(p.property_product_pricelist),
            "active": p.active,
        }

    @api.model
    def _snapshot_product_template(self, t):
        return {
            "name": t.name,
            "default_code": t.default_code or False,
            "barcode": t.barcode or False,
            # Odoo 17: detailed_type in consu/service/product(=storable)/...
            "detailed_type": t.detailed_type,
            "type": t.type,
            "list_price": t.list_price,
            "standard_price": t.standard_price,
            "sale_ok": t.sale_ok,
            "purchase_ok": t.purchase_ok,
            "rent_ok": bool(getattr(t, "rent_ok", False)),
            "invoice_policy": t.invoice_policy,
            "categ_id": self._ref(t.categ_id),
            "uom_id": self._ref(t.uom_id),
            "uom_po_id": self._ref(t.uom_po_id),
            "taxes_id": self._refs(t.taxes_id),
            "supplier_taxes_id": self._refs(t.supplier_taxes_id),
            "description_sale": t.description_sale or False,
            "company_id": self._ref(t.company_id),
            "active": t.active,
            "variants": self._refs(t.product_variant_ids),
        }

    @api.model
    def _snapshot_crm_lead(self, lead):
        return {
            "name": lead.name,
            "type": lead.type,
            "partner_id": self._ref(lead.partner_id),
            "contact_name": lead.contact_name or False,
            "partner_name": lead.partner_name or False,
            "email_from": lead.email_from or False,
            "phone": lead.phone or False,
            "mobile": lead.mobile or False,
            "user_id": self._ref(lead.user_id),
            "team_id": self._ref(lead.team_id),
            "stage_id": self._ref(lead.stage_id),
            "expected_revenue": lead.expected_revenue,
            "probability": lead.probability,
            "date_deadline": lead.date_deadline and lead.date_deadline.isoformat(),
            "priority": lead.priority,
            "tag_ids": self._refs(lead.tag_ids),
            "description": lead.description or False,
            "company_id": self._ref(lead.company_id),
            "lost_reason_id": self._ref(lead.lost_reason_id),
            "active": lead.active,
            "won_status": lead.won_status,
        }

    @api.model
    def _snapshot_sale_order(self, order):
        return {
            "name": order.name,
            "state": order.state,
            "partner_id": self._ref(order.partner_id),
            "partner_invoice_id": self._ref(order.partner_invoice_id),
            "partner_shipping_id": self._ref(order.partner_shipping_id),
            "date_order": order.date_order and order.date_order.isoformat(),
            "validity_date": order.validity_date and order.validity_date.isoformat(),
            "commitment_date": order.commitment_date and order.commitment_date.isoformat(),
            "pricelist_id": self._ref(order.pricelist_id),
            "currency_id": self._ref(order.currency_id),
            "payment_term_id": self._ref(order.payment_term_id),
            "fiscal_position_id": self._ref(order.fiscal_position_id),
            "user_id": self._ref(order.user_id),
            "team_id": self._ref(order.team_id),
            "company_id": self._ref(order.company_id),
            "opportunity_id": self._ref(order.opportunity_id),
            "sale_order_template_id": self._ref(order.sale_order_template_id),
            "client_order_ref": order.client_order_ref or False,
            "origin": order.origin or False,
            "note": order.note or False,
            "is_rental_order": bool(getattr(order, "is_rental_order", False)),
            "rental_start_date": getattr(order, "rental_start_date", False) and order.rental_start_date.isoformat(),
            "rental_return_date": getattr(order, "rental_return_date", False) and order.rental_return_date.isoformat(),
            "amount_untaxed": order.amount_untaxed,
            "amount_tax": order.amount_tax,
            "amount_total": order.amount_total,
            "invoice_ids": self._refs(order.invoice_ids),
            "lines": [self._snapshot_sale_order_line(line) for line in order.order_line.sorted(lambda l: (l.sequence, l.id))],
        }

    @api.model
    def _snapshot_sale_order_line(self, line):
        return {
            "id": line.id,
            "sequence": line.sequence,
            "display_type": line.display_type or False,
            "name": line.name,
            "product_id": self._ref(line.product_id),
            "product_uom_qty": line.product_uom_qty,
            # Odoo 17 names; the Odoo 19 transformer renames them.
            "product_uom": self._ref(line.product_uom),
            "tax_id": self._refs(line.tax_id),
            "price_unit": line.price_unit,
            "discount": line.discount,
            "price_subtotal": line.price_subtotal,
            "price_tax": line.price_tax,
            "price_total": line.price_total,
            "qty_delivered": line.qty_delivered,
            "qty_invoiced": line.qty_invoiced,
            # proquotes (Odoo 17) selection model for optional / multiple sections.
            "selected": getattr(line, "selected", "true"),
            "sectionSelected": getattr(line, "sectionSelected", "true"),
            "special": getattr(line, "special", "regular"),
            "optional": getattr(line, "optional", "no"),
            "quantityLocked": getattr(line, "quantityLocked", "yes"),
            "hiddenSection": getattr(line, "hiddenSection", "no"),
            "applied_name": getattr(line, "applied_name", False) or False,
            "ba_kit_description": getattr(line, "ba_kit_description", False) or False,
            "x_is_rental_kit_component": bool(getattr(line, "x_is_rental_kit_component", False)),
            "is_rental": bool(getattr(line, "is_rental", False)),
            "is_downpayment": line.is_downpayment,
        }

    @api.model
    def _snapshot_account_move(self, move):
        lines = move.invoice_line_ids.sorted(lambda l: (l.sequence, l.id))
        return {
            "name": move.name,
            "move_type": move.move_type,
            "state": move.state,
            "payment_state": move.payment_state,
            "partner_id": self._ref(move.partner_id),
            "partner_shipping_id": self._ref(move.partner_shipping_id),
            "invoice_date": move.invoice_date and move.invoice_date.isoformat(),
            "invoice_date_due": move.invoice_date_due and move.invoice_date_due.isoformat(),
            "date": move.date and move.date.isoformat(),
            "journal_id": self._ref(move.journal_id),
            "currency_id": self._ref(move.currency_id),
            "company_id": self._ref(move.company_id),
            "invoice_payment_term_id": self._ref(move.invoice_payment_term_id),
            "fiscal_position_id": self._ref(move.fiscal_position_id),
            "invoice_user_id": self._ref(move.invoice_user_id),
            "ref": move.ref or False,
            "payment_reference": move.payment_reference or False,
            "invoice_origin": move.invoice_origin or False,
            "narration": move.narration or False,
            "reversed_entry_id": self._ref(move.reversed_entry_id),
            "sale_order_ids": self._refs(lines.sale_line_ids.order_id),
            "amount_untaxed": move.amount_untaxed,
            "amount_tax": move.amount_tax,
            "amount_total": move.amount_total,
            "amount_residual": move.amount_residual,
            "lines": [self._snapshot_account_move_line(line) for line in lines],
        }

    @api.model
    def _snapshot_account_move_line(self, line):
        return {
            "id": line.id,
            "sequence": line.sequence,
            "display_type": line.display_type or False,
            "name": line.name or False,
            "product_id": self._ref(line.product_id),
            "quantity": line.quantity,
            "product_uom_id": self._ref(line.product_uom_id),
            "price_unit": line.price_unit,
            "discount": line.discount,
            "tax_ids": self._refs(line.tax_ids),
            "account_id": self._ref(line.account_id),
            "sale_line_ids": self._refs(line.sale_line_ids),
            "price_subtotal": line.price_subtotal,
            "price_total": line.price_total,
        }
