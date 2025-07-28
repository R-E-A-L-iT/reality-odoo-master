# my_module/controllers/portal.py
from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal

class MyPortal(CustomerPortal):

    def _get_invoices_domain(self, partner):
        domain = super()._get_invoices_domain(partner)
        # Add logic to include documents where partner is a follower
        follower_ids = request.env['mail.followers'].sudo().search([
            ('partner_id', '=', partner.id),
            ('res_model', '=', 'account.move'),
        ]).mapped('res_id')
        if follower_ids:
            domain = ['|'] + domain + [('id', 'in', follower_ids)]
        return domain

    def _get_orders_domain(self, partner):
        domain = super()._get_orders_domain(partner)
        follower_ids = request.env['mail.followers'].sudo().search([
            ('partner_id', '=', partner.id),
            ('res_model', '=', 'sale.order'),
        ]).mapped('res_id')
        if follower_ids:
            domain = ['|'] + domain + [('id', 'in', follower_ids)]
        return domain
