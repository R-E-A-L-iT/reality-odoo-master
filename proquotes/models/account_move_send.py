# -*- coding: utf-8 -*-

import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    @api.depends('checkbox_send_mail')
    def _compute_send_mail_extra_fields(self):
        """
        Override to enable Send button when followers have email addresses,
        even if the customer doesn't have an email.
        """
        for wizard in self:
            wizard.display_mail_composer = wizard.mode == 'invoice_single'
            
            # Find invoices where customer has no email
            invoices_without_customer_email = wizard.move_ids.filtered(lambda x: not x.partner_id.email)
            
            # NEW LOGIC: Check if these invoices have followers with email
            invoices_with_follower_emails = self.env['account.move']
            for invoice in invoices_without_customer_email:
                followers_with_email = invoice.message_partner_ids.filtered(lambda p: p.email and p != invoice.partner_id)
                if followers_with_email:
                    invoices_with_follower_emails |= invoice
                    _logger.info(f"Invoice {invoice.name}: Customer has no email but found {len(followers_with_email)} followers with email")
            
            # Only disable Send button if no customer email AND no follower emails
            invoices_truly_without_email = invoices_without_customer_email - invoices_with_follower_emails
            wizard.send_mail_readonly = invoices_truly_without_email == wizard.move_ids
            
            if not (invoices_truly_without_email and wizard.checkbox_send_mail or wizard.send_mail_readonly):
                wizard.send_mail_warning_message = False
            else:
                # Show warning for invoices that truly have no email recipients
                partners = invoices_truly_without_email.partner_id
                wizard.send_mail_warning_message = {
                    **(wizard.send_mail_warning_message or {}),
                    'partner_missing_email': {
                        'message': _("Partner(s) should have an email address or add followers with email."),
                        'action_text': _("View Partner(s)"),
                        'action': partners._get_records_action(name=_("Check Partner(s)"))
                    }
                }
                
            _logger.info(f"Send button readonly: {wizard.send_mail_readonly} for {len(wizard.move_ids)} invoices")

    @api.model  
    def _send_mails(self, moves_data):
        """
        Override to send emails to followers when customer has no email.
        """
        subtype = self.env.ref('mail.mt_comment')

        for move, move_data in moves_data.items():
            # Check if customer has email OR if followers have email
            customer_has_email = bool(move.partner_id.email)
            followers_with_email = move.message_partner_ids.filtered(lambda p: p.email and p != move.partner_id)
            
            if customer_has_email or followers_with_email:
                mail_template = move_data['mail_template_id']
                mail_lang = move_data['mail_lang']
                mail_params = self._get_mail_params(move, move_data)
                if not mail_params:
                    continue

                # If customer has no email but followers do, send to followers instead
                if not customer_has_email and followers_with_email:
                    _logger.info(f"Invoice {move.name}: Sending to {len(followers_with_email)} followers instead of customer")
                    # Replace the recipient list with followers who have email
                    mail_params['partner_ids'] = followers_with_email.ids

                if move_data.get('proforma_pdf_attachment'):
                    attachment = move_data['proforma_pdf_attachment']
                    mail_params['attachments'].append((attachment.name, attachment.raw))

                email_from = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_from')
                model_description = move.with_context(lang=mail_lang).type_name

                self._send_mail(
                    move,
                    mail_template,
                    subtype_id=subtype.id,
                    model_description=model_description,
                    email_from=email_from,
                    **mail_params,
                )
            else:
                _logger.warning(f"Invoice {move.name}: Skipping email - no customer email and no followers with email")