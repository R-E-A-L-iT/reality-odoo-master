# -*- coding: utf-8 -*-

from odoo import models, api, _
import logging

_logger = logging.getLogger(__name__)


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _process_step_create_lead(self, discuss_channel):
        _logger.info(
            "[LiveChat CRM] _process_step_create_lead CALLED — channel id=%s name=%s step id=%s",
            discuss_channel.id, discuss_channel.name, self.id,
        )

        # --- Call original Odoo lead creation ---
        try:
            lead = super()._process_step_create_lead(discuss_channel)
            _logger.info(
                "[LiveChat CRM] super()._process_step_create_lead returned: %s (id=%s)",
                lead, lead.id if lead else None,
            )
        except Exception as e:
            _logger.error(
                "[LiveChat CRM] super()._process_step_create_lead raised exception for channel %s: %s",
                discuss_channel.id, e,
            )
            lead = None

        # --- Verify lead was created; retry if not ---
        if not lead:
            _logger.warning(
                "[LiveChat CRM] No lead returned by super() for channel %s — attempting fallback creation.",
                discuss_channel.id,
            )
            try:
                lead = discuss_channel._create_lead_from_chatbot_fallback()
                _logger.info(
                    "[LiveChat CRM] Fallback lead creation result: %s (id=%s)",
                    lead, lead.id if lead else None,
                )
            except Exception as e:
                _logger.error(
                    "[LiveChat CRM] Fallback lead creation FAILED for channel %s: %s",
                    discuss_channel.id, e,
                )
                return lead

        if not lead:
            _logger.error(
                "[LiveChat CRM] Lead could NOT be created for channel %s after both attempts. "
                "Channel type=%s, partners=%s",
                discuss_channel.id,
                discuss_channel.channel_type,
                discuss_channel.channel_partner_ids.mapped('name'),
            )
            return lead

        _logger.info(
            "[LiveChat CRM] Lead successfully obtained — id=%s name='%s' user_id=%s",
            lead.id, lead.name, lead.user_id.name if lead.user_id else 'None',
        )

        # --- Link channel to lead if not already linked ---
        if not discuss_channel.livechat_lead_id:
            discuss_channel.livechat_lead_id = lead.id
            _logger.info(
                "[LiveChat CRM] Linked channel %s to lead %s", discuss_channel.id, lead.id
            )

        # --- Build structured Q&A summary ---
        _logger.info("[LiveChat CRM] Building Q&A summary for channel %s", discuss_channel.id)
        qa_summary = self._get_chatbot_qa_summary(discuss_channel)
        _logger.info(
            "[LiveChat CRM] Q&A summary built (%d chars): %s",
            len(qa_summary), qa_summary[:200] if qa_summary else '(empty)',
        )

        # --- Update lead description with Q&A summary ---
        if qa_summary:
            existing_desc = lead.description or ''
            separator = '\n\n' if existing_desc else ''
            lead.description = existing_desc + separator + qa_summary
            _logger.info("[LiveChat CRM] Updated lead %s description with Q&A summary.", lead.id)

        # --- Post full transcript as internal chatter note ---
        try:
            transcript = self._get_chatbot_transcript(discuss_channel)
            _logger.info(
                "[LiveChat CRM] Transcript built (%d chars) for channel %s",
                len(transcript), discuss_channel.id,
            )
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
                _logger.info(
                    "[LiveChat CRM] Posted transcript note to lead %s chatter.", lead.id
                )
        except Exception as e:
            _logger.warning(
                "[LiveChat CRM] Could not post transcript to lead %s: %s", lead.id, e
            )

        # --- Assign configured default salesperson ---
        try:
            default_user_param = self.env['ir.config_parameter'].sudo().get_param(
                'livechat_crm_enhanced.default_lead_user_id'
            )
            _logger.info(
                "[LiveChat CRM] Config param default_lead_user_id = %s", default_user_param
            )
            if default_user_param:
                default_user_id = int(default_user_param)
                if default_user_id:
                    lead.write({'user_id': default_user_id})
                    _logger.info(
                        "[LiveChat CRM] Assigned user_id=%s to lead %s", default_user_id, lead.id
                    )

            default_team_param = self.env['ir.config_parameter'].sudo().get_param(
                'livechat_crm_enhanced.default_lead_team_id'
            )
            _logger.info(
                "[LiveChat CRM] Config param default_lead_team_id = %s", default_team_param
            )
            if default_team_param:
                default_team_id = int(default_team_param)
                if default_team_id:
                    lead.write({'team_id': default_team_id})
                    _logger.info(
                        "[LiveChat CRM] Assigned team_id=%s to lead %s", default_team_id, lead.id
                    )
        except Exception as e:
            _logger.warning(
                "[LiveChat CRM] Could not assign default salesperson to lead %s: %s", lead.id, e
            )

        _logger.info(
            "[LiveChat CRM] _process_step_create_lead COMPLETE for channel %s — lead id=%s",
            discuss_channel.id, lead.id,
        )
        return lead

    def _get_chatbot_qa_summary(self, discuss_channel):
        """
        Build a structured key-value summary from chatbot Q&A messages.
        Pairs each chatbot question with the customer's answer.
        """
        try:
            from odoo.tools import html2plaintext
            messages = discuss_channel.message_ids.sorted('id')
            _logger.info(
                "[LiveChat CRM] _get_chatbot_qa_summary — %d messages in channel %s",
                len(messages), discuss_channel.id,
            )
            lines = []
            last_question = None

            for msg in messages:
                if not msg.body:
                    continue
                plain = html2plaintext(msg.body).strip()
                if not plain:
                    continue

                # Determine chatbot operator partner
                bot_partner = None
                if hasattr(discuss_channel, 'chatbot_current_step_id') and \
                        discuss_channel.chatbot_current_step_id and \
                        discuss_channel.chatbot_current_step_id.chatbot_script_id:
                    bot_partner = discuss_channel.chatbot_current_step_id.chatbot_script_id.operator_partner_id

                is_bot = bot_partner and msg.author_id == bot_partner

                # Fallback: system/no-author messages treated as bot
                if not is_bot and not msg.author_id:
                    is_bot = True

                if is_bot:
                    last_question = plain
                else:
                    if last_question:
                        lines.append('%s: %s' % (last_question, plain))
                        last_question = None
                    else:
                        lines.append(plain)

            return '\n'.join(lines)
        except Exception as e:
            _logger.warning(
                "[LiveChat CRM] _get_chatbot_qa_summary failed for channel %s: %s",
                discuss_channel.id, e,
            )
            return ''

    def _get_chatbot_transcript(self, discuss_channel):
        """
        Return an HTML transcript of the full conversation, oldest first.
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
            _logger.warning(
                "[LiveChat CRM] _get_chatbot_transcript failed for channel %s: %s",
                discuss_channel.id, e,
            )
            return ''
