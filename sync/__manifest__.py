# -*- coding: utf-8 -*-
{
    'name': "Sync",

    'summary': """
        Module that Manages the Syncing between Odoo And Google Sheets""",

    'description': """
        Module that Manages the Syncing between Odoo And Google Sheets
    """,

    'author': "Ty Cyr",

    'license': "LGPL-3",

    # Categories can be used to filter modules in m1dules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical',

    'version': '0.0.122',

    # any module necessary for this one to work correctly
    'depends': ['base', 'proportal', 'proquotes', 'product', 'google_account', 'google_drive'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/schedule.xml',
    ]
}
