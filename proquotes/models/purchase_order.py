# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo import models, fields, api


class purchase_order(models.Model):
    _inherit = "purchase.order"

    date_approve = fields.Datetime(
        string="Confirmation Date",
        copy=False,
        tracking=True,
        readonly=False,
    )

    def _get_available_footer_domain(self):
        return [
            ("active", "=", True),
            ("record_type", "=", "Footer"),
        ]

    @api.model
    def _get_first_available_footer(self, company=False):
        domain = self._get_available_footer_domain()
        footers = self.env["header.footer"].search(domain, order="id asc")
        if company:
            company_specific = footers.filtered(
                lambda f: not f.company_ids or company in f.company_ids
            )
            if company_specific:
                return company_specific[0]
        return footers[:1]

    @api.model
    def _get_user_company_footer(self, user=False, company=False):
        user = user or self.env.user
        company = company or self.env.company

        if not user or not company:
            return self.env["header.footer"]

        line = self.env["res.users.company.footer"].search(
            [
                ("user_id", "=", user.id),
                ("company_id", "=", company.id),
                ("active", "=", True),
            ],
            limit=1,
        )

        if line and line.footer_id and line.footer_id.active and line.footer_id.record_type == "Footer":
            return line.footer_id

        return self.env["header.footer"]

    @api.model
    def _get_company_default_footer(self, company=False):
        company = company or self.env.company
        if (
            company
            and company.default_footer_id
            and company.default_footer_id.active
            and company.default_footer_id.record_type == "Footer"
        ):
            return company.default_footer_id
        return self.env["header.footer"]

    @api.model
    def _default_footer_id(self):
        user = self.env.user
        company = self.env.company

        footer = self._get_user_company_footer(user=user, company=company)
        if footer:
            return footer.id

        footer = self._get_company_default_footer(company=company)
        if footer:
            return footer.id

        footer = self._get_first_available_footer(company=company)
        return footer.id if footer else False

    footer_id = fields.Many2one(
        "header.footer",
        string="Footer",
        required=True,
        domain="[('active', '=', True), ('record_type', '=', 'Footer')]",
        default=_default_footer_id,
    )

    @api.onchange("user_id", "company_id")
    def _onchange_user_or_company_set_footer(self):
        for order in self:
            company = order.company_id or self.env.company
            user = order.user_id or self.env.user

            footer = order._get_user_company_footer(user=user, company=company)
            if not footer:
                footer = order._get_company_default_footer(company=company)
            if not footer:
                footer = order._get_first_available_footer(company=company)

            order.footer_id = footer.id if footer else False

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        user_id = defaults.get("user_id") or self.env.uid
        company_id = defaults.get("company_id") or self.env.company.id

        user = self.env["res.users"].browse(user_id)
        company = self.env["res.company"].browse(company_id)

        footer = self._get_user_company_footer(user=user, company=company)
        if not footer:
            footer = self._get_company_default_footer(company=company)
        if not footer:
            footer = self._get_first_available_footer(company=company)

        if footer:
            defaults["footer_id"] = footer.id

        return defaults
