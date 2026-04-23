from odoo import fields, models


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    ba_email_subject = fields.Char(
        string='Email Subject',
        help='Custom subject used when sending emails from this opportunity.',
    )
    ba_company_name = fields.Char(string='Company Name')
    ba_company_website = fields.Char(string='Company Website')

    def _message_compute_subject(self):
        self.ensure_one()
        if self.ba_email_subject:
            return self.ba_email_subject
        return super()._message_compute_subject()

    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            if record.type == 'opportunity' and record.ba_company_name:
                record._ba_sync_company()
        return records

    def write(self, vals):
        res = super().write(vals)
        # Only run sync if ba_company_name or type is being changed
        if 'ba_company_name' in vals or 'type' in vals:
            for record in self:
                if record.type == 'opportunity' and record.ba_company_name:
                    record._ba_sync_company()
        return res

    def _ba_sync_company(self):
        Partner = self.env['res.partner']
        company_name = self.ba_company_name.strip()

        # Search for existing company by name (case-insensitive)
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

        # Link existing contact to the company
        if self.partner_id and not self.partner_id.is_company:
            if self.partner_id.parent_id != company:
                self.partner_id.parent_id = company
        # No contact yet — set the company as the customer
        elif not self.partner_id:
            self.partner_id = company
