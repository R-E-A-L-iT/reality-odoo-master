# -*- coding: utf-8 -*-

import ast
import base64
from email.policy import default
import re
from math import ceil

from datetime import date, datetime, timedelta
import functools
from functools import partial
from itertools import groupby
import logging

from odoo import api, fields, models, SUPERUSER_ID, _, tools
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tools.misc import formatLang, get_lang
from odoo.osv import expression as exp
from odoo.tools import float_is_zero, float_compare
from odoo import models, fields, api
from odoo.models import BaseModel as BSM
from collections import defaultdict
from odoo.http import request
from odoo.http import Response as Responseht
from odoo.http import FutureResponse as FutureResponseht

_logger = logging.getLogger(__name__)

class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    send_mail_readonly = fields.Boolean(compute='_compute_send_mail_extra_fields', readonly=False)

    def _compute_send_mail_extra_fields(self):
        for wizard in self:
            wizard.display_mail_composer = wizard.mode == 'invoice_single'
            wizard.send_mail_warning_message = False

            invoices_without_mail_data = wizard.move_ids.filtered(lambda x: not x.partner_id.email)
            wizard.send_mail_readonly = invoices_without_mail_data == wizard.move_ids

            if wizard.mode == 'invoice_multi' and wizard.checkbox_send_mail and invoices_without_mail_data:
                wizard.send_mail_warning_message = _(
                    "The partners on the following invoices have no email address, "
                    "so those invoices will not be sent: %s",
                    ", ".join(invoices_without_mail_data.mapped('name')))

    @api.model
    def _send_mails(self, moves_data):
        subtype = self.env.ref('mail.mt_comment')
        _logger.info('>>>>>>>>>>>>>>>584.subtype: %s,', subtype)
        self._generate_dynamic_reports(moves_data)
        
        for move, move_data in [(move, move_data) for move, move_data in moves_data.items()]:
            _logger.info('>>>>>>>>>>>>>>>588.move: %s,', move)
            mail_template = move_data['mail_template_id']
            mail_lang = move_data['mail_lang']
            mail_params = self._get_mail_params(move, move_data)
            if not mail_params:
                continue

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

    def _get_placeholder_mail_attachments_data(self, move):
        """Override to only show placeholder when template has invoice reports configured."""
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
        """Override to only include PDF when mail template has reports configured."""
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
        """
        Check if the mail template has invoice reports configured in Dynamic Reports field.
        
        :param mail_template: mail.template record
        :return: True if invoice reports are configured, False otherwise
        """
        if not mail_template:
            return False
        
        # Check if the template has any reports configured in report_template_ids (Dynamic Reports)
        if mail_template.report_template_ids:
            # Check if any of the configured reports are invoice reports
            invoice_reports = mail_template.report_template_ids.filtered(
                lambda r: r.model == 'account.move' and 'invoice' in r.report_name.lower()
            )
            return bool(invoice_reports)
        
        return False

    def _get_mail_move_values(self, move, wizard=None):
        """Override to handle template-based attachment logic for background processing."""
        result = super()._get_mail_move_values(move, wizard)
        
        # For background processing (when wizard is None), we need to check the stored template
        if not wizard and move.send_and_print_values:
            mail_template_id = move.send_and_print_values.get('mail_template_id')
            if mail_template_id:
                mail_template = self.env['mail.template'].browse(mail_template_id)
                # Rebuild attachment widget based on template configuration
                result['mail_attachments_widget'] = self._get_default_mail_attachments_widget(move, mail_template)
        
        return result