# -*- coding: utf-8 -*-

import logging

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


# Odoo 19: account.move.send is now an AbstractModel (was TransientModel).
# An _inherit-only extension must match the base model's abstract-ness.
class AccountMoveSend(models.AbstractModel):
    _inherit = 'account.move.send'

    send_mail_readonly = fields.Boolean(compute='_compute_send_mail_extra_fields', readonly=False)

    @api.depends('checkbox_send_mail', 'move_ids.partner_id.email', 'move_ids.message_partner_ids')
    def _compute_send_mail_extra_fields(self):
        for wizard in self:
            wizard.display_mail_composer = wizard.mode == 'invoice_single'
            wizard.send_mail_warning_message = False

            invoices_without_customer_email = wizard.move_ids.filtered(lambda m: not m.partner_id.email)

            invoices_with_follower_emails = self.env['account.move']
            for inv in invoices_without_customer_email:
                followers_with_email = inv.message_partner_ids.filtered(lambda p: p.email and p != inv.partner_id)
                if followers_with_email:
                    invoices_with_follower_emails |= inv
                    _logger.info(
                        "Invoice %s: customer has no email but found %d follower(s) with email",
                        inv.name, len(followers_with_email)
                    )

            invoices_truly_without_email = invoices_without_customer_email - invoices_with_follower_emails

            wizard.send_mail_readonly = invoices_truly_without_email == wizard.move_ids

            if wizard.mode == 'invoice_multi' and wizard.checkbox_send_mail and invoices_truly_without_email:
                wizard.send_mail_warning_message = _(
                    "The partners on the following invoices have no email address or followers with email, "
                    "so those invoices will not be sent: %s",
                    ", ".join(invoices_truly_without_email.mapped('name'))
                )

            _logger.info(
                "Send button readonly: %s (total invoices: %d; truly without email: %d)",
                wizard.send_mail_readonly, len(wizard.move_ids), len(invoices_truly_without_email)
            )

    @api.model
    def _send_mails(self, moves_data):
        subtype = self.env.ref('mail.mt_comment')
        _logger.info('>>>>>>>>>>>>>>>584.subtype: %s,', subtype)

        self._generate_dynamic_reports(moves_data)

        for move, move_data in [(mv, md) for mv, md in moves_data.items()]:
            _logger.info('>>>>>>>>>>>>>>>588.move: %s,', move)

            mail_template = move_data['mail_template_id']
            mail_lang = move_data['mail_lang']

            mail_params = self._get_mail_params(move, move_data)
            if not mail_params:
                continue

            customer_has_email = bool(move.partner_id.email)
            followers_with_email = move.message_partner_ids.filtered(lambda p: p.email and p != move.partner_id)

            if not customer_has_email and followers_with_email:
                _logger.info(
                    "Invoice %s: Sending to %d follower(s) instead of customer (no customer email).",
                    move.name, len(followers_with_email)
                )
                mail_params['partner_ids'] = followers_with_email.ids
                if 'email_to' in mail_params:
                    mail_params.pop('email_to', None)

            if move_data.get('proforma_pdf_attachment'):
                attachment = move_data['proforma_pdf_attachment']
                mail_params.setdefault('attachments', [])
                mail_params['attachments'].append((attachment.name, attachment.raw))

            email_from = self._get_mail_default_field_value_from_template(mail_template, mail_lang, move, 'email_from')
            model_description = move.with_context(lang=mail_lang).type_name

            has_any_recipient = customer_has_email or bool(followers_with_email)
            if not has_any_recipient:
                _logger.warning(
                    "Invoice %s: Skipping email - no customer email and no followers with email",
                    move.name
                )
                continue

            self._send_mail(
                move,
                mail_template,
                subtype_id=subtype.id,
                model_description=model_description,
                email_from=email_from,
                **mail_params,
            )

    def _get_placeholder_mail_attachments_data(self, move):
        # If no mail template is selected, use default behavior
        if not hasattr(self, 'mail_template_id') or not self.mail_template_id:
            return super()._get_placeholder_mail_attachments_data(move)

        # Check if the mail template has invoice reports configured
        if not self._should_attach_invoice_pdf(self.mail_template_id):
            return []

        # Use original behavior if reports are configured
        return super()._get_placeholder_mail_attachments_data(move)

    @api.model
    def _get_invoice_extra_attachments_data(self, move):
        # For single invoice mode, check the current wizard's template
        if hasattr(self, 'mode') and self.mode == 'invoice_single' and hasattr(self, 'mail_template_id'):
            if not self._should_attach_invoice_pdf(self.mail_template_id):
                return []
        # For multi invoice mode or cron processing, check the move's stored template
        elif move.send_and_print_values and move.send_and_print_values.get('mail_template_id'):
            mail_template = self.env['mail.template'].browse(move.send_and_print_values.get('mail_template_id'))
            if not self._should_attach_invoice_pdf(mail_template):
                return []

        # Use original behavior if reports are configured or no template context
        return super()._get_invoice_extra_attachments_data(move)

    def _should_attach_invoice_pdf(self, mail_template):
        if not mail_template:
            return False

        # Check if the template has any reports configured in report_template_ids (Dynamic Reports)
        if mail_template.report_template_ids:
            # Check if any of the configured reports are invoice reports
            invoice_reports = mail_template.report_template_ids.filtered(
                lambda r: r.model == 'account.move' and 'invoice' in (r.report_name or '').lower()
            )
            return bool(invoice_reports)

        return False

    def _get_mail_move_values(self, move, wizard=None):
        result = super()._get_mail_move_values(move, wizard)

        # For background processing (when wizard is None), we need to check the stored template
        if not wizard and move.send_and_print_values:
            mail_template_id = move.send_and_print_values.get('mail_template_id')
            if mail_template_id:
                mail_template = self.env['mail.template'].browse(mail_template_id)
                # Rebuild attachment widget based on template configuration
                result['mail_attachments_widget'] = self._get_default_mail_attachments_widget(move, mail_template)

        return result
