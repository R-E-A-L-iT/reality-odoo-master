# -*- coding: utf-8 -*-

from odoo import api, models

PROVINCE_TAX_BY_CODE = {
    "QC": "GST + QST for sales",
    "AB": "GST for sales - 5%",
    "BC": "GST + PST for sales (BC)",
    "ON": "HST for sales - 13%",
    "MB": "GST + PST for sales (MB)",
    "NB": "HST for sales - 15%",
    "NL": "HST for sales - 15%",
    "NT": "GST for sales - 5%",
    "NS": "HST 14%",
    "NU": "GST for sales - 5%",
    "PE": "HST for sales - 15%",
    "SK": "GST + PST for sales (SK)",
    "YT": "GST for sales - 5%",
}


def _code_from_state(state):
    if not state:
        return False

    code = (state.code or "").upper()
    name = (state.display_name or state.name or "").upper()

    if code in PROVINCE_TAX_BY_CODE:
        return code

    if "QUEBEC" in name or "QUÉBEC" in name:
        return "QC"
    if "ALBERTA" in name:
        return "AB"
    if "BRITISH" in name:
        return "BC"
    if "ONTARIO" in name:
        return "ON"
    if "MANITOBA" in name:
        return "MB"
    if "BRUNSWICK" in name:
        return "NB"
    if "NEWFOUNDLAND" in name:
        return "NL"
    if "NORTHWEST" in name:
        return "NT"
    if "SCOTIA" in name:
        return "NS"
    if "NUNAVUT" in name:
        return "NU"
    if "PRINCE" in name:
        return "PE"
    if "SASKATCHEWAN" in name:
        return "SK"
    if "YUKON" in name:
        return "YT"

    return False


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def _is_ca_company_scope_checkout_tax(self):
        self.ensure_one()
        return self.company_id and self.company_id.name == "R-E-A-L.iT Solutions"

    def _get_checkout_shipping_partner(self):
        self.ensure_one()
        return self.partner_shipping_id or self.partner_id

    def _get_checkout_province_tax(self, province_code):
        self.ensure_one()

        if not province_code or not self._is_ca_company_scope_checkout_tax():
            return self.env["account.tax"]

        tax_name = PROVINCE_TAX_BY_CODE.get(province_code)
        if not tax_name:
            return self.env["account.tax"]

        return (
            self.env["account.tax"]
            .with_company(self.company_id)
            .search([("name", "=", tax_name)], limit=1)
        )

    def _apply_website_canadian_province_taxes(self):
        """
        Apply province taxes to website cart lines so totals are visible during checkout.
        """
        for order in self:
            if not order.website_id:
                continue

            if not order._is_ca_company_scope_checkout_tax():
                continue

            shipping_partner = order._get_checkout_shipping_partner()
            lines = order.order_line.filtered(lambda l: not l.display_type and l.product_id)

            if not lines:
                continue

            # If no shipping address yet, or not Canada, show no tax for now
            if not shipping_partner or shipping_partner.country_id.code != "CA":
                lines.with_context(skip_checkout_tax_line_hook=True).write({
                    "tax_id": [(5, 0, 0)]
                })
                continue

            state = shipping_partner.state_id
            if not state:
                lines.with_context(skip_checkout_tax_line_hook=True).write({
                    "tax_id": [(5, 0, 0)]
                })
                continue

            province_code = _code_from_state(state)
            province_tax = order._get_checkout_province_tax(province_code)

            if province_tax:
                lines.with_context(skip_checkout_tax_line_hook=True).write({
                    "tax_id": [(6, 0, province_tax.ids)]
                })
            else:
                lines.with_context(skip_checkout_tax_line_hook=True).write({
                    "tax_id": [(5, 0, 0)]
                })

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        website_orders = orders.filtered(lambda o: o.website_id)
        if website_orders:
            website_orders._apply_website_canadian_province_taxes()
        return orders

    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get("skip_checkout_tax_order_hook"):
            return res

        trigger_fields = {
            "partner_id",
            "partner_shipping_id",
            "company_id",
            "website_id",
            "pricelist_id",
            "fiscal_position_id",
        }

        if trigger_fields & set(vals.keys()):
            self.filtered(lambda o: o.website_id).with_context(
                skip_checkout_tax_order_hook=True
            )._apply_website_canadian_province_taxes()

        return res

    def _cart_update(self, *args, **kwargs):
        res = super()._cart_update(*args, **kwargs)
        self._apply_website_canadian_province_taxes()
        return res


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)

        if self.env.context.get("skip_checkout_tax_line_hook"):
            return lines

        orders = lines.mapped("order_id").filtered(lambda o: o.website_id)
        if orders:
            orders.with_context(
                skip_checkout_tax_line_hook=True,
                skip_checkout_tax_order_hook=True,
            )._apply_website_canadian_province_taxes()

        return lines

    def write(self, vals):
        res = super().write(vals)

        if self.env.context.get("skip_checkout_tax_line_hook"):
            return res

        trigger_fields = {
            "product_id",
            "product_uom_qty",
            "price_unit",
            "discount",
            "order_id",
        }

        if trigger_fields & set(vals.keys()):
            orders = self.mapped("order_id").filtered(lambda o: o.website_id)
            if orders:
                orders.with_context(
                    skip_checkout_tax_line_hook=True,
                    skip_checkout_tax_order_hook=True,
                )._apply_website_canadian_province_taxes()

        return res

    def unlink(self):
        if self.env.context.get("skip_checkout_tax_line_hook"):
            return super().unlink()

        orders = self.mapped("order_id").filtered(lambda o: o.website_id)
        res = super().unlink()

        if orders:
            orders.with_context(
                skip_checkout_tax_line_hook=True,
                skip_checkout_tax_order_hook=True,
            )._apply_website_canadian_province_taxes()

        return res