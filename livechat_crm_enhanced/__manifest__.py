{
    'name': 'LiveChat CRM Enhanced',
    'version': '17.0.1.0.0',
    'category': 'Sales/CRM',
    'summary': 'Enhanced LiveChat integration with CRM lead creation',
    'description': """
        This module enhances the LiveChat functionality by adding:
        * Create Lead button in chat header
        * Automatic lead creation from chat conversations
        * Chat history integrated into lead log notes
        * Update Lead functionality for ongoing conversations
    """,
    'author': 'Braincrew Apps',
    'website': 'https://www.braincrewapps.com',
    'depends': [
        'base',
        'mail',
        'crm',
        'im_livechat',
        'crm_livechat',
        'web',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/utm_data.xml',
        'views/discuss_channel_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'livechat_crm_enhanced/static/src/js/thread_actions.js',
        ],
        'im_livechat.embed_assets': [
            'livechat_crm_enhanced/static/src/js/thread_actions.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}