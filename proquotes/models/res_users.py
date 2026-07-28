from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
        if line and line.footer_id and line.footer_id.active and line.footer_id.document_type == "footer":
            return line.footer_id

        if (
            company
            and company.default_footer_id
            and company.default_footer_id.active
            and company.default_footer_id.document_type == "footer"
        ):
            return company.default_footer_id

        footer = self.env["quotation.document"].search(
            [
                ("active", "=", True),
                ("doc_class", "=", "preview"), ("document_type", "=", "footer"),
            ],
            order="id asc",
        ).filtered(lambda f: not f.company_ids or company in f.company_ids)[:1]

        return footer or self.env["quotation.document"]


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
        "quotation.document",
        string="Default Footer",
        required=True,
        domain="[('active', '=', True), ('doc_class', '=', 'preview'), ('document_type', '=', 'footer')]",
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
            if record.footer_id and record.footer_id.document_type != "footer":
                raise ValidationError(_("The selected record must be a Footer."))