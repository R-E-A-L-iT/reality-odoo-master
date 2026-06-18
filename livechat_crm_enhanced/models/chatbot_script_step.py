# -*- coding: utf-8 -*-

from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _process_step_create_lead(self, discuss_channel):
        """
        Override to:
        1. Call super() to run standard lead creation
        2. Verify a lead was actually created — retry if not
        3. Enrich the lead with full chatbot Q&A summary + transcript
        4. Assign configured default salesperson
        """
        lead = super()._process_step_create_lead(discuss_channel)

        # --- Verify lead was created; retry if not ---
        if not lead:
            _logger.warning(
                "Chatbot 'create_lead' step returned no lead for channel %s — retrying.",
                discuss_channel.id,
            )
            try:
                lead = discuss_channel._create_lead_from_chatbot_fallback()
            except Exception as e:
                _logger.error(
                    "Fallback lead creation failed for channel %s: %s",
                    discuss_channel.id, e,
                )
                return lead

        if not lead:
            _logger.error(
                "Lead could not be created for chatbot channel %s after retry.",
                discuss_channel.id,
            )
            return lead

        # --- Link channel to lead if not already linked ---
        if not discuss_channel.livechat_lead_id:
            discuss_channel.livechat_lead_id = lead.id

        # --- Build structured Q&A summary ---
        qa_summary = self._get_chatbot_qa_summary(discuss_channel)

        # --- Update lead description with Q&A summary ---
        if qa_summary:
            existing_desc = lead.description or ''
            separator = '\n\n' if existing_desc else ''
            lead.description = existing_desc + separator + qa_summary

        # --- Post full transcript as internal chatter note ---
        try:
            transcript = self._get_chatbot_transcript(discuss_channel)
            if transcript:
                lead.message_post(
                    body=_(
                        '<strong>Chatbot Conversation Summary</strong><br/><br/>'
                        '%s'
                        '<br/><br/><strong>Full Conversation Transcript:</strong><br/>%s'
                    ) % (qa_summary.replace('\n', '<br/>'), transcript),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
        except Exception as e:
            _logger.warning("Could not post transcript to lead %s: %s", lead.id, e)

        # --- Assign configured default salesperson ---
        try:
            default_user_param = self.env['ir.config_parameter'].sudo().get_param(
                'livechat_crm_enhanced.default_lead_user_id'
            )
            if default_user_param:
                default_user_id = int(default_user_param)
                if default_user_id:
                    lead.write({'user_id': default_user_id})

            default_team_param = self.env['ir.config_parameter'].sudo().get_param(
                'livechat_crm_enhanced.default_lead_team_id'
            )
            if default_team_param:
                default_team_id = int(default_team_param)
                if default_team_id:
                    lead.write({'team_id': default_team_id})
        except Exception as e:
            _logger.warning("Could not assign default salesperson to lead %s: %s", lead.id, e)

        return lead

    def _get_chatbot_qa_summary(self, discuss_channel):
        """
        Build a structured key-value summary from chatbot Q&A messages.
        Pairs each chatbot question with the customer's answer.
        """
        messages = discuss_channel.message_ids.sorted('id')
        lines = []
        last_question = None

        for msg in messages:
            if not msg.body:
                continue
            from odoo.tools import html2plaintext
            plain = html2plaintext(msg.body).strip()
            if not plain:
                continue

            # Determine if message is from the chatbot or the visitor/customer
            is_bot = (
                msg.author_id
                and msg.author_id == discuss_channel.chatbot_current_step_id.chatbot_script_id.operator_partner_id
            ) if hasattr(discuss_channel, 'chatbot_current_step_id') else False

            # Fallback: messages without a human partner are treated as bot messages
            if not is_bot and msg.author_id:
                # Check if this author is a portal/public user (= customer)
                user = self.env['res.users'].sudo().search(
                    [('partner_id', '=', msg.author_id.id)], limit=1
                )
                is_bot = not (user and user.share or not user)

            if is_bot or not msg.author_id:
                last_question = plain
            else:
                if last_question:
                    lines.append('%s: %s' % (last_question, plain))
                    last_question = None
                else:
                    lines.append(plain)

        return '\n'.join(lines)

    def _get_chatbot_transcript(self, discuss_channel):
        """
        Return a plain-text transcript of the full conversation, oldest first.
        """
        try:
            from odoo.tools import html2plaintext
            messages = discuss_channel.message_ids.sorted('id')
            lines = []
            for msg in messages:
                if not msg.body:
                    continue
                plain = html2plaintext(msg.body).strip()
                if not plain:
                    continue
                author = msg.author_id.name if msg.author_id else _('System')
                ts = msg.date.strftime('%Y-%m-%d %H:%M') if msg.date else ''
                lines.append('[%s] %s: %s' % (ts, author, plain))
            return '<br/>'.join(lines)
        except Exception as e:
            _logger.warning("Error building transcript for channel %s: %s", discuss_channel.id, e)
            return ''
