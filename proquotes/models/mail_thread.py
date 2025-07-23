# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def _notify_get_recipients_groups(self, message, model_description, msg_vals=None):
        groups = super()._notify_get_recipients_groups(message, model_description, msg_vals=msg_vals)

        if not self:
            return groups

        self.ensure_one()

        # Fetch access link (requires portal.mixin inheritance)
        if not isinstance(self, self.env.registry['portal.mixin']):
            return groups

        access_token = self._portal_ensure_token()
        access_link = self.get_portal_url()

        for group in groups:
            group_name, match_func, options = group

            if group_name == 'follower':
                options['active'] = True
                options['has_button_access'] = True
                options['button_access'] = {
                    'url': access_link,
                    'title': _('View Invoice') if self._name == 'account.move' else _('View Document')
                }

        return groups

    @api.model
    def _notify_prepare_template_context(self, message):
        ctx = super()._notify_prepare_template_context(message)
        user = message.author_id.user_ids and message.author_id.user_ids[0] or self.env.user

        ctx.update({
            'signature_can': user.signature_can or '',
            'signature_usa': user.signature_usa or '',
        })
        return ctx