{
    'name': 'Chatter Google Message Button',
    'version': '17.0.1.0.0',
    'category': 'Mail',
    'summary': 'Adds a Google Message button to the chatter for CRM leads',
    'description': '''
        This module adds a new "Send Google Message" button to the chatter
        for CRM leads. When the simple_email_layout field is True, emails
        are sent without headers and footers.
    ''',
    'author': 'RealIT Custom',
    'depends': ['mail', 'crm'],
    'data': [
        # 'views/res_users_extend.xml',
    ],
    "assets": {
        'web.assets_backend': [
            "chatter_google_message/static/src/xml/chatter_templates.xml",
            "chatter_google_message/static/src/js/chatter_patch.js",
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
}