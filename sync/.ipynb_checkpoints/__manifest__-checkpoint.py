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

    'version': '0.6',
    
    # any module necessary for this one to work correctly
    'depends': ['base', 'proportal', 'product', 'google_account', 'google_drive'],
    
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/schedule.xml',
    ],
}
