from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.osv import expression

class CustomCustomerPortal(CustomerPortal):

    def _get_invoices_domain(self, partner):
        domain = super()._get_invoices_domain(partner)

        # Existing behavior: followers can see it
        follower_domain = [('message_partner_ids', 'in', [partner.id])]
        domain = expression.OR([domain, follower_domain])

        # New behavior: portal admin can see invoices addressed to their portal companies
        if partner.portal_administrator:
            allowed_company_ids = partner.get_portal_company_commercial_ids()
            admin_domain = [('partner_id.commercial_partner_id', 'in', allowed_company_ids)]
            domain = expression.OR([domain, admin_domain])

        return domain