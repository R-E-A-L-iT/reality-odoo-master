# -*- coding: utf-8 -*-
{
    'name': "Proquotes",

    'summary': """
        Quote Upgrade Module that adds Advanced Features""",

    'description': """
        Module that allows advanced Quote features. Like Folding Sections, Improved Optional Products, and Multiple Choice Sections
    """,

    'author': "Ty Cyr",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',

    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'product' ,'website', 'sale_management', 'sale', 'digest', 'portal'],
    
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/quotesFrontend.xml',
        'views/quotesBackend.xml',
        'views/mail.xml',
        'views/portalAccess.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
