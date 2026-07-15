# -*- coding: utf-8 -*-

from odoo import models, _
import logging

_logger = logging.getLogger(__name__)


class ChatbotScriptStep(models.Model):
    _inherit = 'chatbot.script.step'

    def _process_step_create_lead(self, discuss_channel):
        """
        Override crm_livechat's _process_step_create_lead.

        The core Odoo method creates a lead but does NOT return it, so we
        replicate the creation logic here to keep a reference, then enrich
        the lead with the full Q&A summary, transcript, and configured
        default salesperson.
        """
        _logger.info(
            "[LiveChat CRM] _process_step_create_lead — channel id=%s name=%s step_type=%s",
            discuss_channel.id, discuss_channel.name, self.step_type,
        )

        # --- Replicate crm_livechat lead-creation logic (without calling super)
        # so we hold a reference to the created record.
        try:
            customer_values = self._chatbot_prepare_customer_values(
                discuss_channel, create_partner=False, update_partner=True,
            )
            _logger.debug(
                "[LiveChat CRM] customer_values — email=%s phone=%s",
                customer_values.get('email'), customer_values.get('phone'),
            )
        except Exception as e:
            _logger.error(
                "[LiveChat CRM] _chatbot_prepare_customer_values failed for channel %s: %s",
                discuss_channel.id, e,
            )
            return False

        if self.env.user._is_public():
            create_values = {
                'email_from': customer_values.get('email'),
                'phone': customer_values.get('phone'),
            }
            _logger.info("[LiveChat CRM] Public user — using email/phone as lead contact.")
        else:
            partner = self.env.user.partner_id
            create_values = {
                'partner_id': partner.id,
                'company_id': partner.company_id.id,
            }
            _logger.debug(
                "[LiveChat CRM] Logged-in user — partner=%s id=%s",
                partner.name, partner.id,
            )

        # Base lead values from crm_livechat (includes channel history in description)
        try:
            lead_vals = self._chatbot_crm_prepare_lead_values(
                discuss_channel, customer_values.get('description', ''),
            )
            _logger.debug(
                "[LiveChat CRM] Base lead values: name=%s team_id=%s type=%s",
                lead_vals.get('name'), lead_vals.get('team_id'), lead_vals.get('type'),
            )
        except Exception as e:
            _logger.error(
                "[LiveChat CRM] _chatbot_crm_prepare_lead_values failed for channel %s: %s",
                discuss_channel.id, e,
            )
            return False

        create_values.update(lead_vals)

        # Always create as opportunity (not a lead requiring qualification)
        create_values['type'] = 'opportunity'

        # --- Apply configured default salesperson (overrides the False set by crm_livechat)
        default_user_id = self._get_default_lead_user_id()
        default_team_id = self._get_default_lead_team_id()
        if default_user_id:
            create_values['user_id'] = default_user_id
            _logger.info("[LiveChat CRM] Applying default user_id=%s", default_user_id)
        if default_team_id:
            create_values['team_id'] = default_team_id
            _logger.info("[LiveChat CRM] Applying default team_id=%s", default_team_id)

        # --- Create the lead
        try:
            lead = self.env['crm.lead'].create(create_values)
            _logger.info(
                "[LiveChat CRM] Lead created — id=%s user_id=%s",
                lead.id, lead.user_id.id if lead.user_id else 'None',
            )
        except Exception as e:
            _logger.error(
                "[LiveChat CRM] crm.lead.create failed for channel %s: %s",
                discuss_channel.id, e,
            )
            return False

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
            chatbot_messages = discuss_channel.chatbot_message_ids.sorted('id')
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
