# -*- coding: utf-8 -*-
{
    'name': "Sync",

    'summary': """
        Module that Manages the Syncing between Odoo And Google Sheets""",

    'description': """
        Module that Manages the Syncing between Odoo And Google Sheets
    """,

    'author': "Ty Cyr",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical',
    'version': '0.8',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product'],
    
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/schedule.xml',
        #'views/quotesFrontend.xml',
        #'views/quotesBackend.xml',
    ],
}
