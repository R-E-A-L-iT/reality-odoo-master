from odoo import http
from odoo.http import request
from odoo.fields import Domain
from odoo.addons.portal.controllers.portal import CustomerPortal

class CustomCustomerPortal(CustomerPortal):

    def _get_orders_domain(self, partner):
        # Odoo 19 combines this with `&` on fields.Domain objects, so returning
        # the plain list odoo.osv.expression built in 17 raises
        # "unsupported operand type(s) for &". See portal_invoice.py.
        domain = Domain(super()._get_orders_domain(partner))

        # Existing behavior: followers can see it
        domain |= Domain('message_partner_ids', 'in', [partner.id])

        # New behavior: portal admin can see orders addressed to their portal companies
        if partner.portal_administrator:
            allowed_company_ids = partner.get_portal_company_commercial_ids()
            domain |= Domain('partner_id.commercial_partner_id', 'in', allowed_company_ids)

        return domain
