{
    'name': 'CRM Enhancements',
    'version': '17.0.1.0.0',
    'category': 'CRM',
    'summary': 'CRM enhancements: custom email subject, and future CRM improvements',
    'author': 'Braincrew Apps',
    'website': 'https://www.braincrewapps.com',
    'depends': ['crm'],
    'data': [
        'views/crm_lead_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'ba_crm_enhancements/static/src/js/composer_patch.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
