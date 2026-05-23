# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResUsersCompanyFooter(models.Model):
    _name = "res.users.company.footer"
    _description = "User Default Footer Per Company"
    _order = "user_id, company_id"

    user_id = fields.Many2one(
        "res.users",
        string="User",
        required=True,
        ondelete="cascade",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        required=True,
        ondelete="cascade",
    )

    footer_id = fields.Many2one(
        "header.footer",
        string="Default Footer",
        required=True,
        domain="[('active', '=', True), ('record_type', '=', 'Footer')]",
        ondelete="restrict",
    )

    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "unique_user_company_footer",
            "unique(user_id, company_id)",
            "Only one default footer can be defined per user and company.",
        ),
    ]

    @api.constrains("footer_id")
    def _check_footer_type(self):
        for record in self:
            if record.footer_id and record.footer_id.record_type != "Footer":
                raise ValidationError(_("The selected record must be a Footer."))
