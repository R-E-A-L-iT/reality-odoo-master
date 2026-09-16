import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, **kwargs):
        if kwargs.get("body") and self._name != "discuss.channel":
            try:
                kwargs["body"] = self.env["promessaging.subuser"]._highlight_mentions(kwargs["body"])
            except Exception:
                _logger.exception("ProMessaging: could not highlight sub-user mentions")
        message = super().message_post(**kwargs)
        try:
            self._promessaging_dispatch_subusers(message)
        except Exception:
            # a webhook must never cost the user their message
            _logger.exception("ProMessaging: sub-user dispatch failed")
        return message

    def _message_compute_author(self, author_id=None, email_from=None, raise_on_email=True):
        """Attribute anything an AI sub-user does to that sub-user's identity.

        Covers messages, notifications and the tracking logs Odoo posts when a
        record is created or changed.
        """
        if author_id is None and not email_from:
            subuser = self.env["promessaging.subuser"]._active_subuser()
            if subuser:
                partner = subuser.sudo()._ensure_partner()
                if partner:
                    return partner.id, partner.email_formatted or email_from
        return super()._message_compute_author(
            author_id=author_id, email_from=email_from, raise_on_email=raise_on_email
        )

    def _promessaging_dispatch_subusers(self, message):
        """Send the message to every sub-user pinged in it."""
        if self.env.context.get("promessaging_skip_subuser_dispatch"):
            return
        if not message or self._name == "discuss.channel" or len(self) != 1:
            return
        # never let one bot's message trigger another round
        if message.subuser_id:
            return
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
