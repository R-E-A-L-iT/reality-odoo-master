# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    confirmation_mail_template = fields.Many2one(
        'mail.template',
        string='Order Confirmation Email',
        related='website_id.confirmation_mail_template_id',
        domain="[('model', '=', 'sale.order')]",
        readonly=False,
        help="Email template to use when sending order confirmation emails for orders created from this website."
    )
