# -*- coding: utf-8 -*-

import logging
from email.utils import make_msgid

from odoo import models

_logger = logging.getLogger(__name__)


class MailMail(models.Model):
    """Give every outgoing email its own Message-Id.

    THE BUG
    -------
    ``mail.mail`` ``_inherits`` ``mail.message``, so ``mail.message_id`` is read
    from the shared mail_message row. When one posted message notifies several
    recipient GROUPS (Odoo builds one mail.mail per group — e.g. internal users
    vs. portal/followers), every one of those distinct emails goes out carrying
    the SAME Message-Id. Core does this in
    ``mail.mail._prepare_outgoing_list`` (``'message_id': self.message_id``).

    That violates RFC 5322 — two different messages must not share a Message-Id —
    and mail infrastructure reacts badly to it. On this deployment the relay saw
    two messages with one id, merged them into a single transaction and rewrote
    the To: header to the union of the recipients. The visible symptoms were:

      * the customer received the email TWICE, and
      * one of those copies was the INTERNAL group's body, so it carried the
        internal user's portal tracking link instead of the customer's.

    Odoo itself was correct throughout: one message, one notification per
    partner, one mail.mail per group each with a single recipient and no raw
    email_to. The damage was done entirely at the transport layer, caused by the
    duplicated header.

    THE FIX
    -------
    Stamp a unique Message-Id on each outgoing email, keeping the domain part so
    it still looks like it came from this host.

    Threading is preserved: Odoo routes incoming replies by matching the
    In-Reply-To / References headers against known ``mail.message.message_id``
    values, so the ORIGINAL id is kept in References. A reply therefore still
    lands on the right record even though it now references an id that differs
    from the one in the Message-Id header.
    """
    _inherit = 'mail.mail'

    def _proquotes_unique_message_id(self, base_message_id, index, partner):
        """Build a Message-Id unique to this (mail, recipient) pair.

        Reuses the domain of the id core would have sent so the value still
        resolves to this host; the local part is freshly generated, which is what
        guarantees uniqueness.
        """
        domain = None
        if base_message_id and '@' in base_message_id:
            domain = base_message_id.rsplit('@', 1)[-1].rstrip('>').strip()
        idstring = 'openerp-%s-%s-m%s-p%s-%s' % (
            self.res_id or 0,
            self.model or '',
            self.id or 0,
            partner.id if partner else 0,
            index,
        )
        try:
            return make_msgid(idstring=idstring, domain=domain or None)
        except Exception:  # malformed domain — fall back to the default host
            return make_msgid(idstring=idstring)

    def _prepare_outgoing_list(self, mail_server=False, doc_to_followers=None):
        emails = super()._prepare_outgoing_list(
            mail_server=mail_server, doc_to_followers=doc_to_followers
        )

        original_message_id = (self.message_id or '').strip()

        for index, email in enumerate(emails):
            partner = email.get('partner_id')

            # Keep the id core would have used in References, so replies still
            # thread onto this record (message_route matches References against
            # stored mail.message.message_id values).
            references = (email.get('references') or '').strip()
            if original_message_id and original_message_id not in references:
                references = ('%s %s' % (references, original_message_id)).strip()
            email['references'] = references

            email['message_id'] = self._proquotes_unique_message_id(
                original_message_id, index, partner
            )

        return emails
