# -*- coding: utf-8 -*-
"""Odoo 17 snapshot -> Odoo 19 values.

Every version difference lives here, not in the handlers:

* core renames: sale.order.line ``product_uom`` -> ``product_uom_id``,
  ``tax_id`` -> ``tax_ids``; product ``detailed_type`` -> ``type`` +
  ``is_storable``;
* proquotes (Odoo 17) line selection model -> proquotes (Odoo 19) sections:

  ========================================  ======================================
  Odoo 17                                   Odoo 19
  ========================================  ======================================
  section ``special == 'optional'``         section ``is_optional = True``
  section ``special == 'multiple'``         section ``x_single_choice = True``
  line ``selected == 'false'`` (qty kept,   line ``product_uom_qty = 0`` and
  subtotal forced to 0)                     ``x_preset_qty = <Odoo 17 qty>``
  line ``sectionSelected == 'false'``       same as unselected
  ========================================  ======================================

Extend with ``_inherit = "upgrade.sync.transformer"``.
"""
from odoo import api, fields, models


def _date(value):
    return value and fields.Date.to_date(value[:10])


def _datetime(value):
    return value and fields.Datetime.to_datetime(value.replace("T", " ")[:19])


def _drop_empty(vals, keys):
    """Let Odoo 19 compute its own default instead of forcing an empty value
    on fields that Odoo 19 fills automatically (required or defaulted)."""
    for key in keys:
        if key in vals and not vals[key]:
            del vals[key]
    return vals


class UpgradeSyncTransformer(models.AbstractModel):
    _name = "upgrade.sync.transformer"
    _description = "Upgrade Sync Odoo 17 -> Odoo 19 Transformer"

    @property
    def _resolver(self):
        return self.env["upgrade.sync.resolver"]

    # ------------------------------------------------------------------
    # Contacts / products / CRM
    # ------------------------------------------------------------------
    @api.model
    def _partner_vals(self, snap):
        r = self._resolver
        vals = {
            "name": snap["name"],
            "is_company": snap.get("is_company"),
            "parent_id": r._resolve_id(snap.get("parent_id")),
            "type": snap.get("type") or "contact",
            "email": snap.get("email"),
            "phone": snap.get("phone"),
            "street": snap.get("street"),
            "street2": snap.get("street2"),
            "city": snap.get("city"),
            "zip": snap.get("zip"),
            "state_id": r._resolve_id(snap.get("state_id"), required=False),
            "country_id": r._resolve_id(snap.get("country_id"), required=False),
            "vat": snap.get("vat"),
            "ref": snap.get("ref"),
            "website": snap.get("website"),
            "function": snap.get("function"),
            "company_id": r._resolve_id(snap.get("company_id")),
            "user_id": r._resolve_id(snap.get("user_id"), required=False),
            "category_id": [(6, 0, r._resolve_ids(snap.get("category_ids"), required=False))],
            "active": snap.get("active", True),
        }
        # Odoo 19 core removed res.partner.mobile; proquotes/prophone re-add it.
        if "mobile" in self.env["res.partner"]._fields:
            vals["mobile"] = snap.get("mobile")
        if snap.get("lang") and self.env["res.lang"].sudo().search_count([("code", "=", snap["lang"])]):
            vals["lang"] = snap["lang"]
        if snap.get("property_payment_term_id"):
            vals["property_payment_term_id"] = r._resolve_id(snap["property_payment_term_id"], required=False)
        if snap.get("property_product_pricelist"):
            vals["property_product_pricelist"] = r._resolve_id(snap["property_product_pricelist"], required=False)
        if vals["type"] not in dict(self.env["res.partner"]._fields["type"].selection):
            vals["type"] = "other"
        return vals

    @api.model
    def _product_template_vals(self, snap):
        r = self._resolver
        vals = {
            "name": snap["name"],
            "default_code": snap.get("default_code"),
            "barcode": snap.get("barcode") or False,
            "list_price": snap.get("list_price"),
            "standard_price": snap.get("standard_price"),
            "sale_ok": snap.get("sale_ok"),
            "purchase_ok": snap.get("purchase_ok"),
            "invoice_policy": snap.get("invoice_policy") or "order",
            "categ_id": r._resolve_id(snap.get("categ_id")),
            "uom_id": r._resolve_id(snap.get("uom_id")),
            "taxes_id": [(6, 0, r._resolve_ids(snap.get("taxes_id")))],
            "supplier_taxes_id": [(6, 0, r._resolve_ids(snap.get("supplier_taxes_id")))],
            "description_sale": snap.get("description_sale"),
            "company_id": r._resolve_id(snap.get("company_id")),
            "active": snap.get("active", True),
        }
        # Odoo 17 detailed_type 'product' (storable) -> Odoo 19 consu + is_storable
        detailed = snap.get("detailed_type") or snap.get("type")
        if detailed == "service":
            vals["type"] = "service"
        elif detailed == "combo":
            vals["type"] = "combo"
        else:
            vals["type"] = "consu"
            vals["is_storable"] = detailed == "product"
        if "rent_ok" in self.env["product.template"]._fields:
            vals["rent_ok"] = snap.get("rent_ok")
        return vals

    @api.model
    def _lead_vals(self, snap):
        r = self._resolver
        vals = {
            "name": snap["name"],
            "type": snap.get("type") or "opportunity",
            "partner_id": r._resolve_id(snap.get("partner_id")),
            "contact_name": snap.get("contact_name"),
            "partner_name": snap.get("partner_name"),
            "email_from": snap.get("email_from"),
            "phone": snap.get("phone"),
            "user_id": r._resolve_id(snap.get("user_id"), required=False),
            "team_id": r._resolve_id(snap.get("team_id"), required=False),
            "expected_revenue": snap.get("expected_revenue"),
            "date_deadline": _date(snap.get("date_deadline")),
            "priority": snap.get("priority") or "0",
            "tag_ids": [(6, 0, r._resolve_ids(snap.get("tag_ids"), required=False))],
            "description": snap.get("description"),
            "company_id": r._resolve_id(snap.get("company_id")),
        }
        if "mobile" in self.env["crm.lead"]._fields:
            vals["mobile"] = snap.get("mobile")
        return _drop_empty(vals, ("company_id", "date_deadline"))

    # ------------------------------------------------------------------
    # Sales
    # ------------------------------------------------------------------
    @api.model
    def _sale_order_vals(self, snap):
        r = self._resolver
        vals = {
            "partner_id": r._resolve_id(snap.get("partner_id")),
            "partner_invoice_id": r._resolve_id(snap.get("partner_invoice_id")),
            "partner_shipping_id": r._resolve_id(snap.get("partner_shipping_id")),
            "date_order": _datetime(snap.get("date_order")),
            "validity_date": _date(snap.get("validity_date")),
            "commitment_date": _datetime(snap.get("commitment_date")),
            "pricelist_id": r._resolve_id(snap.get("pricelist_id")),
            "payment_term_id": r._resolve_id(snap.get("payment_term_id")),
            "fiscal_position_id": r._resolve_id(snap.get("fiscal_position_id")),
            "user_id": r._resolve_id(snap.get("user_id"), required=False),
            "team_id": r._resolve_id(snap.get("team_id"), required=False),
            "company_id": r._resolve_id(snap.get("company_id")),
            "opportunity_id": r._resolve_id(snap.get("opportunity_id")),
            "sale_order_template_id": r._resolve_id(snap.get("sale_order_template_id"), required=False) or False,
            "client_order_ref": snap.get("client_order_ref"),
            "origin": snap.get("origin"),
            "note": snap.get("note"),
        }
        if snap.get("is_rental_order") and "is_rental_order" in self.env["sale.order"]._fields:
            vals.update({
                "is_rental_order": True,
                "rental_start_date": _datetime(snap.get("rental_start_date")),
                "rental_return_date": _datetime(snap.get("rental_return_date")),
            })
        return _drop_empty(vals, (
            "partner_invoice_id", "partner_shipping_id", "date_order", "validity_date",
            "commitment_date", "pricelist_id", "payment_term_id", "fiscal_position_id",
            "team_id", "company_id",
        ))

    @api.model
    def _sale_line_mode(self, lines):
        """Yield (line, section_mode) where section_mode is the Odoo 17
        ``special`` value of the section the line belongs to."""
        mode = "regular"
        for line in lines:
            if line.get("display_type") == "line_section":
                mode = line.get("special") or "regular"
            yield line, mode

    @api.model
    def _sale_line_vals(self, line, section_mode):
        """Values for one Odoo 19 sale.order.line (without order_id)."""
        r = self._resolver
        display_type = line.get("display_type") or False
        vals = {
            "sequence": line.get("sequence"),
            "display_type": display_type,
            "name": line.get("name"),
        }
        if display_type == "line_section":
            special = line.get("special") or "regular"
            vals["is_optional"] = special == "optional"
            vals["x_single_choice"] = special == "multiple"
            return vals
        if display_type:
            return vals
        qty = line.get("product_uom_qty") or 0.0
        selected = line.get("selected") != "false" and line.get("sectionSelected") != "false"
        vals.update({
            "product_id": r._resolve_id(line.get("product_id")),
            "product_uom_id": r._resolve_id(line.get("product_uom")),   # 17: product_uom
            "tax_ids": [(6, 0, r._resolve_ids(line.get("tax_id")))],     # 17: tax_id
            "price_unit": line.get("price_unit"),
            "discount": line.get("discount"),
            # Odoo 17 keeps the qty of an unselected line and zeroes its subtotal;
            # Odoo 19 models "unselected" as qty 0 with the qty kept as preset.
            "product_uom_qty": qty if selected else 0.0,
            "x_preset_qty": max(qty, 1.0),
            "ba_kit_description": line.get("ba_kit_description") or False,
        })
        return _drop_empty(vals, ("product_uom_id",))

    @api.model
    def _sale_lines(self, snap):
        """[(odoo17_line_snapshot, odoo19_vals)] for the lines to replay."""
        result = []
        for line, mode in self._sale_line_mode(snap.get("lines") or []):
            if line.get("x_is_rental_kit_component") or line.get("is_downpayment"):
                # rental kit components are generated by proquotes itself;
                # down payments are created by the invoicing wizard (later phase)
                continue
            result.append((line, self._sale_line_vals(line, mode)))
        return result

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------
    @api.model
    def _move_vals(self, snap):
        r = self._resolver
        vals = {
            "move_type": snap["move_type"],
            "partner_id": r._resolve_id(snap.get("partner_id")),
            "partner_shipping_id": r._resolve_id(snap.get("partner_shipping_id"), required=False),
            "invoice_date": _date(snap.get("invoice_date")),
            "invoice_date_due": _date(snap.get("invoice_date_due")),
            "journal_id": r._resolve_id(snap.get("journal_id")),
            "currency_id": r._resolve_id(snap.get("currency_id")),
            "company_id": r._resolve_id(snap.get("company_id")),
            "invoice_payment_term_id": r._resolve_id(snap.get("invoice_payment_term_id"), required=False),
            "fiscal_position_id": r._resolve_id(snap.get("fiscal_position_id"), required=False),
            "invoice_user_id": r._resolve_id(snap.get("invoice_user_id"), required=False),
            "ref": snap.get("ref"),
            "payment_reference": snap.get("payment_reference"),
            "invoice_origin": snap.get("invoice_origin"),
            "narration": snap.get("narration"),
        }
        return _drop_empty(vals, (
            "partner_shipping_id", "invoice_date", "invoice_date_due", "journal_id", "currency_id",
            "company_id", "invoice_payment_term_id", "fiscal_position_id", "invoice_user_id",
        ))

    @api.model
    def _move_header_update_vals(self, snap):
        """Fields that may be aligned on an existing draft invoice."""
        vals = self._move_vals(snap)
        for fname in ("move_type", "company_id", "journal_id", "currency_id"):
            vals.pop(fname, None)
        if vals.get("invoice_payment_term_id"):
            vals.pop("invoice_date_due", None)
        return vals

    @api.model
    def _move_line_vals(self, line):
        r = self._resolver
        display_type = line.get("display_type") or "product"
        vals = {
            "sequence": line.get("sequence"),
            "display_type": display_type,
            "name": line.get("name"),
        }
        if display_type != "product":
            return vals
        vals.update({
            "product_id": r._resolve_id(line.get("product_id"), required=False),
            "quantity": line.get("quantity"),
            "product_uom_id": r._resolve_id(line.get("product_uom_id"), required=False),
            "price_unit": line.get("price_unit"),
            "discount": line.get("discount"),
            "tax_ids": [(6, 0, r._resolve_ids(line.get("tax_ids")))],
        })
        if line.get("account_id"):
            vals["account_id"] = r._resolve_id(line["account_id"])
        return _drop_empty(vals, ("product_uom_id",))

    @api.model
    def _move_lines(self, snap):
        return [
            (line, self._move_line_vals(line))
            for line in snap.get("lines") or []
            if (line.get("display_type") or "product") in ("product", "line_section", "line_note")
        ]
