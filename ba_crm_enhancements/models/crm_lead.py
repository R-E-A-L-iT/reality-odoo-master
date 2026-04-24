from odoo import api, fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    ba_email_subject = fields.Char(
        string='Email Subject',
        help='Custom subject used when sending emails from this opportunity.',
    )
    ba_company_name = fields.Char(
        string='Company Name',
        compute='_compute_ba_company_fields',
        store=True,
        readonly=False,
    )
    ba_company_website = fields.Char(
        string='Company Website',
        compute='_compute_ba_company_fields',
        store=True,
        readonly=False,
    )

    def _message_compute_subject(self):
        self.ensure_one()
        if self.ba_email_subject:
            return self.ba_email_subject
        return super()._message_compute_subject()

    @api.depends('partner_id')
    def _compute_ba_company_fields(self):
        for record in self:
            partner = record.partner_id
            if not partner:
                continue
            company = partner if partner.is_company else partner.parent_id
            if company:
                if not record.ba_company_name:
                    record.ba_company_name = company.name
                if not record.ba_company_website:
                    record.ba_company_website = company.website or False

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.type == 'opportunity' and record.ba_company_name:
                record._ba_sync_company()
        return records

    def write(self, vals):
        res = super().write(vals)
        if 'ba_company_name' in vals or 'type' in vals:
            for record in self:
                if record.type == 'opportunity' and record.ba_company_name:
                    record._ba_sync_company()
        return res

    def _ba_sync_company(self):
        Partner = self.env['res.partner']
        company_name = self.ba_company_name.strip()

        company = Partner.search([
            ('is_company', '=', True),
            ('name', '=ilike', company_name),
        ], limit=1)

        if not company:
            company = Partner.create({
                'name': company_name,
                'is_company': True,
                'website': self.ba_company_website or False,
            })
        elif self.ba_company_website and not company.website:
            company.website = self.ba_company_website

        if self.partner_id and not self.partner_id.is_company:
            if self.partner_id.parent_id != company:
                self.partner_id.parent_id = company
        elif not self.partner_id:
            self.partner_id = company
