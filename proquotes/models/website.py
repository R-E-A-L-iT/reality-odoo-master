# -*- coding: utf-8 -*-

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    def _default_quote_send_mail_template(self):
        """Get the default eCommerce quote send email template."""
        try:
            return self.env.ref('proquotes.mail_template_ecommerce_quote_send', raise_if_not_found=False) or \
                   self.env['mail.template'].search([('name', '=', 'eCommerce Quote Send')], limit=1).id
        except ValueError:
            return False

    quote_send_mail_template_id = fields.Many2one(
        'mail.template',
        string='Quote Send Email Template',
        default=_default_quote_send_mail_template,
        domain="[('model', '=', 'sale.order')]",
        help="Email template to use when sending quotes for orders created from this website."
    )
