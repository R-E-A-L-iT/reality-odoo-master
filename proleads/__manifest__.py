
{
    'name': 'ProLeads',
    'author': 'Ezekiel J. deBlois',
    'version': "19.0.1.0.0",
    "license": "LGPL-3",
    'summary': 'Adds automation for lead registration',
    'description': ' ',
    'depends': ['base', 'crm', 'website_crm'],
    "data": [
        "views/leadsBackend.xml",
        "views/crm_stage.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'proleads/static/src/js/composer_patch.js',
        ],
    },
    'installable': True,
    'application': True,
}