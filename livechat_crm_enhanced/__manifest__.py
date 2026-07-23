{
    'name': 'LiveChat CRM Enhanced',
    'version': '19.0.2.0.0',
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
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        # Odoo 19 migration: temporarily disabled. This "Create Lead" thread action
        # (a) was declared in im_livechat.embed_assets — the restricted public
        # livechat-widget bundle that can't resolve backend imports (@mail/core,
        # useService, rpc), which fails the bundle build and blanks the client — and
        # (b) uses the v17 thread-action definition shape; the mail thread-action API
        # changed in v18/19. Re-add it (backend bundle only, ported to the v19
        # registerThreadAction API) once reviewed. The livechat_channel_count field
        # and the rest of the module stay active (version bump kept).
        # 'web.assets_backend': [
        #     'livechat_crm_enhanced/static/src/js/thread_actions.js',
        # ],
        # 'im_livechat.embed_assets': [
        #     'livechat_crm_enhanced/static/src/js/thread_actions.js',
        # ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}