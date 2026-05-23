# -*- coding: utf-8 -*-

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    company_footer_line_ids = fields.One2many(
        "res.users.company.footer",
        "user_id",
        string="Company Default Footers",
    )

    def get_default_footer_for_company(self, company=False):
        self.ensure_one()
        company = company or self.env.company

        line = self.company_footer_line_ids.filtered(
            lambda l: l.active and l.company_id == company
        )[:1]
        if line and line.footer_id and line.footer_id.active and line.footer_id.record_type == "Footer":
            return line.footer_id

        if (
            company
            and company.default_footer_id
            and company.default_footer_id.active
            and company.default_footer_id.record_type == "Footer"
        ):
            return company.default_footer_id

        footer = self.env["header.footer"].search(
            [
                ("active", "=", True),
                ("record_type", "=", "Footer"),
            ],
            order="id asc",
        ).filtered(lambda f: not f.company_ids or company in f.company_ids)[:1]

        return footer or self.env["header.footer"]
