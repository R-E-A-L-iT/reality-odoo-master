import logging

from odoo import models

_logger = logging.getLogger(__name__)


class MailThread(models.AbstractModel):
    _inherit = "mail.thread"

    def message_post(self, **kwargs):
        # someone typed the name anyway: drop them rather than notify them
        if kwargs.get("partner_ids"):
            partners = self.env["res.partner"].browse(kwargs["partner_ids"])
            blocked = partners._promessaging_unpingable()
            if blocked:
                kwargs["partner_ids"] = [
                    pid for pid in kwargs["partner_ids"] if pid not in set(blocked.ids)
                ]
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
        # never create anything here: building the identity itself posts
        # messages, which would come straight back into this method
        if (
            author_id is None
            and not email_from
            and not self.env.context.get("promessaging_building_identity")
        ):
            subuser = self.env["promessaging.subuser"]._active_subuser()
            partner = subuser.sudo().partner_id if subuser else None
            if partner:
                return partner.id, (
                    partner.email_formatted
                    or subuser.sudo().user_id.partner_id.email_formatted
                    or email_from
                )
        return super()._message_compute_author(
            author_id=author_id, email_from=email_from, raise_on_email=raise_on_email
        )

    def _notify_get_recipients(self, message, msg_vals, **kwargs):
        """A ping in a log note must reach the person by email.

        Odoo only emails a mentioned user whose notification preference is
        "email"; anyone on "inbox" would just get a bell. Mentions in notes are
        deliberate, so they are forced to email.
        """
        recipients = super()._notify_get_recipients(message, msg_vals, **kwargs)
        values = msg_vals or {}
        mentioned = set(values.get("partner_ids") or message.sudo().partner_ids.ids or [])
        if not mentioned:
            return recipients
        subtype_id = values.get("subtype_id") or message.sudo().subtype_id.id
        note_subtype = self.env.ref("mail.mt_note", raise_if_not_found=False)
        if not note_subtype or subtype_id != note_subtype.id:
            return recipients
        for recipient in recipients:
            if recipient.get("id") in mentioned and recipient.get("notif") == "inbox":
                recipient["notif"] = "email"
        return recipients

    def _promessaging_dispatch_subusers(self, message):
        """Send the message to every sub-user pinged in it."""
        if self.env.context.get("promessaging_skip_subuser_dispatch"):
            return
        if not message or self._name == "discuss.channel" or len(self) != 1:
            return
        # never let one bot's message trigger another round
        if message.sudo().subuser_id:
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
