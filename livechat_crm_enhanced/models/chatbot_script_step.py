# -*- coding: utf-8 -*-

from odoo import models, _
import logging

_logger = logging.getLogger(__name__)


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _process_step_create_lead(self, discuss_channel):
        """
        Extend crm_livechat's _process_step_create_lead: let it create the
        lead (including its own default team/user assignment logic), then
        enrich it with the configured default salesperson/team, a Q&A
        summary, and the full transcript.
        """
        lead = super()._process_step_create_lead(discuss_channel)
        if not lead:
            return lead

        # Always create as opportunity (not a lead requiring qualification),
        # and apply the configured default salesperson/team if any.
        vals = {'type': 'opportunity'}
        default_user_id = self._get_default_lead_user_id()
        default_team_id = self._get_default_lead_team_id()
        if default_user_id:
            vals['user_id'] = default_user_id
        if default_team_id:
            vals['team_id'] = default_team_id
        lead.write(vals)

        discuss_channel.livechat_lead_id = lead.id

        qa_summary = self._get_chatbot_qa_summary(discuss_channel)
        if qa_summary:
            existing_desc = lead.description or ''
            separator = '\n\n' if existing_desc else ''
            lead.description = existing_desc + separator + '\n\n--- Chatbot Answers ---\n' + qa_summary

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

        _logger.info("[LiveChat CRM] Enriched lead %s from channel %s", lead.id, discuss_channel.id)
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
            chatbot_messages = discuss_channel.chatbot_message_ids.sorted('id')
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
