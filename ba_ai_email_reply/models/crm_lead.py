# -*- coding: utf-8 -*-
import logging
from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools.mail import html2plaintext

_logger = logging.getLogger(__name__)

OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1'
DEFAULT_MODEL = 'openai/gpt-4o-mini'


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def action_generate_ai_reply(self):
        """
        Collect last 10 chatter messages + workspace Knowledge articles,
        call OpenRouter API (OpenAI-compatible), and return the generated reply text.

        Called from JS via this.orm.call('crm.lead', 'action_generate_ai_reply', [[id]]).
        Returns: {'reply': str}
        """
        self.ensure_one()

        # ── 1. Config params ────────────────────────────────────────────────
        get = self.env['ir.config_parameter'].sudo().get_param

        api_key = get('ba_ai_email_reply.api_key')
        if not api_key:
            raise UserError(_(
                "OpenRouter API key is not configured. "
                "Go to Settings → General Settings → AI Email Reply."
            ))

        model_name = get('ba_ai_email_reply.model') or DEFAULT_MODEL

        # ── 2. Collect chatter messages ─────────────────────────────────────
        messages = self.message_ids.filtered(
            lambda m: m.message_type in ('email', 'comment') and m.body
        )[:10]
        messages = messages.sorted('date')  # oldest → newest

        if not messages:
            raise UserError(_("No messages found in this conversation yet."))

        latest_msg = messages[-1]
        latest_author = latest_msg.author_id.name or _('Customer')
        latest_body = html2plaintext(latest_msg.body).strip()

        history_lines = []
        for msg in messages[:-1]:
            author = msg.author_id.name or _('Unknown')
            body = html2plaintext(msg.body).strip()
            if body:
                history_lines.append(f"{author}: {body}")

        # ── 3. Fetch Knowledge articles (workspace, not trashed) ────────────
        articles = self.env['knowledge.article'].search([
            ('category', '=', 'workspace'),
            ('is_template', '=', False),
            ('to_delete', '=', False),
            ('active', '=', True),
        ], limit=20)

        knowledge_parts = []
        for article in articles:
            title = article.name or ''
            body = html2plaintext(article.body or '').strip()
            if body:
                knowledge_parts.append(f"### {title}\n{body}")

        knowledge_text = (
            '\n\n'.join(knowledge_parts)
            if knowledge_parts
            else "No company knowledge articles available."
        )

        # ── 4. Build prompt ─────────────────────────────────────────────────
        system_prompt = (
            "You are a professional sales assistant. "
            "Use the provided company knowledge accurately. "
            "Keep replies polite, concise, and professional. "
            "Do not make up facts not present in the company knowledge."
        )

        history_section = '\n'.join(history_lines) if history_lines else 'None'

        user_prompt = (
            f"Customer's latest message (from {latest_author}):\n"
            f"{latest_body}\n\n"
            f"--- Previous conversation history ---\n"
            f"{history_section}\n\n"
            f"--- Company Knowledge ---\n"
            f"{knowledge_text}\n\n"
            f"Please write a professional email reply to the customer's latest message."
        )

        # ── 5. Call OpenRouter (OpenAI-compatible endpoint) ─────────────────
        try:
            from openai import OpenAI  # lazy import
        except ImportError:
            raise UserError(_(
                "The 'openai' Python package is not installed. "
                "Please run: pip install openai"
            ))

        try:
            client = OpenAI(
                api_key=api_key,
                base_url=OPENROUTER_BASE_URL,
            )
            response = client.chat.completions.create(
                model=model_name,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': user_prompt},
                ],
                max_tokens=800,
                temperature=0.7,
            )
            generated_reply = response.choices[0].message.content.strip()
        except Exception as e:
            _logger.error("OpenRouter API error for lead %s: %s", self.id, e)
            raise UserError(_("OpenRouter API error: %s") % str(e))

        return {'reply': generated_reply}
