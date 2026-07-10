
{
    'name': 'ProLeads',
    'author': 'Ezekiel J. deBlois',
    'version': '1.2',
    "license": "LGPL-3",
    'summary': 'Adds automation for lead registration',
    'description': ' ',
    'depends': ['base', 'crm', 'website_crm', 'procontact'],
    "data": [
        "security/ir.model.access.csv",
        "views/leadsBackend.xml",
        "views/crm_stage.xml",
        "views/leica_register_wizard.xml",
        "views/res_config_settings.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'proleads/static/src/js/composer_patch.js',
        ],
    },
    'installable': True,
    'application': True,
}