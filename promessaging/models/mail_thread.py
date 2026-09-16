import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, **kwargs):
        message = super().message_post(**kwargs)
        try:
            self._promessaging_dispatch_subusers(message)
        except Exception:
            # a webhook must never cost the user their message
            _logger.exception("ProMessaging: sub-user dispatch failed")
        return message

    def _promessaging_dispatch_subusers(self, message):
        """Send the message to every sub-user pinged in it."""
        if self.env.context.get("promessaging_skip_subuser_dispatch"):
            return
        if not message or self._name == "discuss.channel" or len(self) != 1:
            return
        # never let one bot's message trigger another round
        author_user = message.author_id.user_ids[:1]
        if author_user and author_user.is_ai_user:
            return
        subusers = self.env["promessaging.subuser"]._find_mentioned(message.body)
        for subuser in subusers:
            subuser.notify_prompt(message, self)

    def unlink(self):
        # a deleted document must not leave its draft behind
        self.env["promessaging.draft"].sudo().search([
            ("res_model", "=", self._name), ("res_id", "in", self.ids),
        ]).unlink()
        return super().unlink()
