from odoo.addons.account.controllers.portal import PortalAccount


class PortalAccountInh(PortalAccount):
    def _get_invoices_domain(self):
        return [('state', 'not in', ('cancel', 'draft')), (
        'move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'in_receipt'))]