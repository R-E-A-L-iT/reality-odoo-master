# -*- coding: utf-8 -*-
{
    'name': 'AI Email Reply Suggestions (CRM)',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'Generate AI-powered email reply suggestions in CRM chatter using OpenAI',
    'author': 'Braincrew Apps',
    'website': 'https://www.braincrewapps.com',
    'depends': ['crm', 'mail', 'base_setup', 'knowledge'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ba_ai_email_reply/static/src/xml/chatter_templates.xml',
            'ba_ai_email_reply/static/src/js/chatter_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
