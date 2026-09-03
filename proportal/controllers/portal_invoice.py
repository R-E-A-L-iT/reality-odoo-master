from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.fields import Domain
from odoo.http import request


class CustomCustomerPortal(CustomerPortal):

    def _get_invoices_domain(self, partner=None):
        # Odoo 19 builds the portal invoice domain with fields.Domain and
        # combines it as `Domain(...) & self._get_invoices_domain()`, so this
        # must return a Domain — not the plain list odoo.osv.expression used to
        # produce in 17. Core also calls it with no arguments now (the old
        # `invoice_type` parameter is gone), so nothing is forwarded to super().
        domain = Domain(super()._get_invoices_domain())

        # Resolve partner properly
        if partner is None:
            partner = request.env.user.partner_id

        # Existing behavior: followers can see it
        domain |= Domain('message_partner_ids', 'in', [partner.id])

        # New behavior: portal admin can see invoices addressed to their portal companies
        if partner.portal_administrator:
            allowed_company_ids = partner.get_portal_company_commercial_ids()
            domain |= Domain('partner_id.commercial_partner_id', 'in', allowed_company_ids)

        return domain
