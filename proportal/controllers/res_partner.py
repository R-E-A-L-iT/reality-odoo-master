from odoo import api, fields, models
# (keep your existing imports)

class ResPartner(models.Model):
    _inherit = "res.partner"

    def get_portal_company_commercial_ids(self):
        """Return allowed portal company ids normalized to commercial partners."""
        self.ensure_one()
        partners = self.env["res.partner"].sudo().browse(self.get_portal_company_ids()).exists()
        return partners.mapped("commercial_partner_id").ids

    def portal_admin_can_access_partner(self, target_partner):
        """True if self is portal admin and target partner belongs to one of their portal companies."""
        self.ensure_one()
        if not self.portal_administrator:
            return False
        if not target_partner:
            return False
        allowed_commercial_ids = set(self.get_portal_company_commercial_ids())
        return target_partner.commercial_partner_id.id in allowed_commercial_ids