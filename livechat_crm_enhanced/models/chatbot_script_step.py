# -*- coding: utf-8 -*-

from odoo import models, _
import logging

_logger = logging.getLogger(__name__)


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _process_step_create_lead(self, discuss_channel):
        """Enrich the lead crm_livechat creates from a chatbot step.

        Odoo 19's implementation returns the lead, so this calls super and
        then applies the configured owner, links the channel, and posts the
        Q&A summary plus transcript. Leads are stored as opportunities.
        """
        _logger.info(
            "[LiveChat CRM] _process_step_create_lead — channel id=%s name=%s step_type=%s",
            discuss_channel.id, discuss_channel.name, self.step_type,
        )
        lead = super()._process_step_create_lead(discuss_channel)
        if not lead:
            return lead

        updates = {'type': 'opportunity'}
        default_user_id = self._get_default_lead_user_id()
        default_team_id = self._get_default_lead_team_id()
        if default_user_id:
            updates['user_id'] = default_user_id
            _logger.info("[LiveChat CRM] Applying default user_id=%s", default_user_id)
        if default_team_id:
            updates['team_id'] = default_team_id
            _logger.info("[LiveChat CRM] Applying default team_id=%s", default_team_id)
        lead.write(updates)

        # --- Link channel to lead
        try:
            discuss_channel.livechat_lead_id = lead.id
            _logger.info(
                "[LiveChat CRM] Linked channel %s → lead %s", discuss_channel.id, lead.id,
            )
        except Exception as e:
            _logger.warning(
                "[LiveChat CRM] Could not link channel to lead: %s", e,
            )

        # --- Build Q&A summary from chatbot messages and append to description
        qa_summary = ''
        try:
            qa_summary = self._get_chatbot_qa_summary(discuss_channel)
            _logger.debug(
                "[LiveChat CRM] Q&A summary (%d chars): %s",
                len(qa_summary), qa_summary[:300] if qa_summary else '(empty)',
            )
            if qa_summary:
                existing_desc = lead.description or ''
                separator = '\n\n' if existing_desc else ''
                lead.description = existing_desc + separator + '\n\n--- Chatbot Answers ---\n' + qa_summary
        except Exception as e:
            _logger.warning(
                "[LiveChat CRM] Could not build Q&A summary for lead %s: %s", lead.id, e,
            )

        # --- Post full transcript as internal chatter note
        try:
            transcript = self._get_chatbot_transcript(discuss_channel)
            if transcript:
                lead.message_post(
                    body=_(
                        '<strong>Chatbot Conversation Summary</strong><br/><br/>'
                        '%s'
                        '<br/><br/><strong>Full Conversation Transcript:</strong><br/>%s'
                    ) % (
                        (qa_summary or '').replace('\n', '<br/>'),
                        transcript,
                    ),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
                _logger.info(
                    "[LiveChat CRM] Posted transcript note to lead %s chatter.", lead.id,
                )
        except Exception as e:
            _logger.warning(
                "[LiveChat CRM] Could not post transcript to lead %s: %s", lead.id, e,
            )

        _logger.info(
            "[LiveChat CRM] _process_step_create_lead COMPLETE — lead id=%s", lead.id,
        )
        return lead

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_default_lead_user_id(self):
        try:
            val = self.env['ir.config_parameter'].sudo().get_param(
                'livechat_crm_enhanced.default_lead_user_id'
            )
            return int(val) if val else False
        except Exception:
            return False

    def _get_default_lead_team_id(self):
        try:
            val = self.env['ir.config_parameter'].sudo().get_param(
                'livechat_crm_enhanced.default_lead_team_id'
            )
            return int(val) if val else False
        except Exception:
            return False

    def _get_chatbot_qa_summary(self, discuss_channel):
        """
        Pair each chatbot question with the customer's typed answer.
        Uses chatbot.message records which store the step + user raw answer.
        """
        try:
            from odoo.tools import html2plaintext
            lines = []
            # chatbot.message links each step's message to the user's raw answer
            chatbot_messages = discuss_channel.sudo().chatbot_message_ids.sorted('id')
            _logger.info(
                "[LiveChat CRM] chatbot_message_ids count=%d for channel %s",
                len(chatbot_messages), discuss_channel.id,
            )
            for cm in chatbot_messages:
                step = cm.script_step_id
                if not step:
                    continue
                question = html2plaintext(step.message or '').strip()
                if not question:
                    continue
                # user_raw_answer is set for question_email / question_phone steps
                if cm.user_raw_answer:
                    answer = html2plaintext(cm.user_raw_answer).strip()
                    lines.append('%s: %s' % (question, answer))
                elif step.step_type == 'question_selection' and cm.user_script_answer_id:
                    lines.append('%s: %s' % (question, cm.user_script_answer_id.name))

            return '\n'.join(lines)
        except Exception as e:
            _logger.warning(
                "[LiveChat CRM] _get_chatbot_qa_summary error for channel %s: %s",
                discuss_channel.id, e,
            )
            return ''

    def _get_chatbot_transcript(self, discuss_channel):
        """Full plain-text transcript, oldest message first."""
        try:
            from odoo.tools import html2plaintext
            lines = []
            for msg in discuss_channel.message_ids.sorted('id'):
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
            _logger.warning(
                "[LiveChat CRM] _get_chatbot_transcript error for channel %s: %s",
                discuss_channel.id, e,
            )
            return ''
