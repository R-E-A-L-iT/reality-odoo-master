# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    quote_send_mail_template = fields.Many2one(
        'mail.template',
        string='Quote Send Email Template',
        related='website_id.quote_send_mail_template_id',
        domain="[('model', '=', 'sale.order')]",
        readonly=False,
        help="Email template to use when sending quotes for orders created from this website."
    )
