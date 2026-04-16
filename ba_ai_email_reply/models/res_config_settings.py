# -*- coding: utf-8 -*-
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    ba_ai_api_key = fields.Char(
        string='OpenRouter API Key',
        config_parameter='ba_ai_email_reply.api_key',
        help='API key from openrouter.ai. Stored securely server-side — never sent to the browser.',
    )

    ba_ai_model = fields.Char(
        string='Model',
        config_parameter='ba_ai_email_reply.model',
        help=(
            'OpenRouter model identifier, e.g. openai/gpt-4o-mini, '
            'anthropic/claude-3-haiku, google/gemini-flash-1.5. '
            'Leave empty to use the default: openai/gpt-4o-mini.'
        ),
    )
