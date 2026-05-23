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
        Collect last 10 chatter messages + the selected Knowledge article,
        call OpenRouter API, and return the generated reply text.

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
        # message_ids are ordered by -id (newest first); slice 10, then sort oldest→newest
        messages = self.message_ids.filtered(
            lambda m: m.message_type in ('email', 'comment') and m.body
        )[:10]
        messages = messages.sorted('date')

        if not messages:
            raise UserError(_("No messages found in this conversation yet."))

        latest_msg = messages[-1]
        latest_body = html2plaintext(latest_msg.body).strip()

        history_lines = []
        for msg in messages[:-1]:
            author = msg.author_id.name or _('Unknown')
            body = html2plaintext(msg.body).strip()
            if body:
                history_lines.append(f"{author}: {body}")

        # ── 3. Fetch selected Knowledge article ─────────────────────────────
        article_id_str = get('ba_ai_email_reply.knowledge_article_id')
        knowledge_text = "No company knowledge document selected."

        if article_id_str:
            try:
                article = self.env['knowledge.article'].browse(int(article_id_str)).exists()
                if article:
                    body = html2plaintext(article.body or '').strip()
                    knowledge_text = (
                        f"### {article.name}\n{body}"
                        if body
                        else "Selected knowledge document has no content."
                    )
            except (ValueError, TypeError):
                pass

        # ── 4. Build prompt ─────────────────────────────────────────────────
        company_name = self.env.company.name or 'our company'
        company_user = self.env.user.name or 'Sales Team'

        system_prompt = (
            f"You are {company_user}, a professional sales representative at {company_name}. "
            "You are writing an email reply ON BEHALF OF THE COMPANY to the customer. "
            "Always write in first person as a company representative — never as the customer. "
            "Use the provided company knowledge accurately. "
            "Keep replies polite, concise, and professional. "
            "Do not make up facts not present in the company knowledge."
        )

        history_section = '\n'.join(history_lines) if history_lines else 'None'

        user_prompt = (
            f"The customer sent the following message:\n"
            f"{latest_body}\n\n"
            f"--- Previous conversation history ---\n"
            f"{history_section}\n\n"
            f"--- Company Knowledge ---\n"
            f"{knowledge_text}\n\n"
            f"Write a professional reply from {company_user} at {company_name} to the customer's message above."
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
