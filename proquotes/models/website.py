# -*- coding: utf-8 -*-

from odoo import fields, models


class Website(models.Model):
    _inherit = 'website'

    def _default_confirmation_mail_template(self):
        """Get the default confirmation email template."""
        try:
            return self.env.ref('sale.mail_template_sale_confirmation').id
        except ValueError:
            return False

    confirmation_mail_template_id = fields.Many2one(
        'mail.template',
        string='Order Confirmation Email',
        default=_default_confirmation_mail_template,
        domain="[('model', '=', 'sale.order')]",
        help="Email template to use when sending order confirmation emails for orders created from this website."
    )
