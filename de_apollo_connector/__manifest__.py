# -*- coding: utf-8 -*-
{
    'name': "Apollo Connector",
    'summary': """
        Effortlessly Sync Opportunities and Contacts Between Odoo and Apollo
    """,
    'description': """
        Our Apollo-Odoo Integration Module is your key to seamless lead and contact management. This module facilitates the easy import and export of opportunities and contacts between Odoo and Apollo, ensuring that your sales and marketing teams stay synchronized and efficient. Say goodbye to data duplication and hello to a streamlined workflow that maximizes your lead generation efforts. Experience a new level of productivity and collaboration by integrating these two powerful platforms.
    """,
    'author': "Dynexcel",
    'website': "https://www.dynexcel.com",
    'category': 'Sales/Marketing',
    'version': '0.4',
    'live_test_url': 'https://youtu.be/_qKgJmMrVq4',
    'depends': ['crm'],
    'data': [
        'security/ir.model.access.csv',
        'data/apollo_data.xml',
        'views/res_config_settings_views.xml',
        'views/apollo_views.xml',
        'views/apollo_instance_views.xml',
        'views/res_partner_category_views.xml',
        'views/res_partner_views.xml',
        'views/crm_lead_views.xml',
        'views/crm_tag_views.xml',
        'views/crm_stage_views.xml',
        'wizards/people_search_wizard_views.xml',
        #'wizards/companies_search_wizard_views.xml',
        'wizards/apl_ops_wizard_views.xml',
        'views/apl_people_views.xml',
        'views/apl_companies_views.xml',
        'wizards/send_data_wizard_views.xml',
        'wizards/convert_data_wizard_views.xml',
    ],
    'assets': {
       'web.assets_backend': [
           'de_apollo_connector/static/src/js/button_search.js',
           'de_apollo_connector/static/src/xml/button_search.xml',
       ],
    },
    'license': 'OPL-1',
    'price': 110,
    'currency': 'USD',
    'images': ['static/description/banner.gif'],
    'installable': True,
    'application': True,
    'auto_install': False,
}
