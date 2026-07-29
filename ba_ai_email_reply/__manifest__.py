# -*- coding: utf-8 -*-
{
    'name': 'AI Email Reply Suggestions (CRM)',
    'version': '19.0.1.0.0',
    'category': 'CRM',
    'summary': 'Generate AI-powered email reply suggestions in CRM chatter using OpenAI',
    'author': 'Braincrew Apps',
    'website': 'https://www.braincrewapps.com',
    'depends': ['crm', 'mail', 'base_setup', 'knowledge'],
    'data': [
        'views/res_config_settings_views.xml',
    ],
    # NOTE (Odoo 19 migration): the chatter assets are temporarily disabled. The
    # "Generate AI Reply" button relied on Chatter.toggleComposer(), which v19
    # removed in the chatter refactor (the composer-open flow moved out of
    # chatter.js), so the button no longer works, and the OWL template inherit
    # anchors on `o-mail-Chatter-sendMessage` which may have changed — a bad
    # inherit anchor breaks the whole web.assets_backend bundle. Keeping the field
    # + settings view (so res.config.settings loads) but deferring the button until
    # it is rebuilt against v19's new composer API. The backend model method
    # (crm.lead.action_generate_ai_reply) is untouched and ready for the rebuild.
    'assets': {
        'web.assets_backend': [
            # 'ba_ai_email_reply/static/src/xml/chatter_templates.xml',
            # 'ba_ai_email_reply/static/src/js/chatter_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
