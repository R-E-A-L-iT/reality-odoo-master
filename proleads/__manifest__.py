
{
    'name': 'ProLeads',
    'author': 'Ezekiel J. deBlois',
    'version': "19.0.1.1.0",
    "license": "LGPL-3",
    'summary': 'Adds automation for lead registration',
    'description': ' ',
    # website + website_crm_iap_reveal added when the ProMeasure functionality was
    # merged in: they provide the website.visitor and crm.reveal.rule/crm.reveal.view
    # models the merged code extends.
    'depends': ['base', 'crm', 'website_crm', 'website', 'website_crm_iap_reveal'],
    "data": [
        "views/leadsBackend.xml",
        "views/crm_stage.xml",
        # Merged from ProMeasure: adds IP address to the website visitor views.
        "views/website_visitor_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'proleads/static/src/js/composer_patch.js',
        ],
    },
    'installable': True,
    'application': True,
}