# -*- coding: utf-8 -*-
{
    'name': "quoteGenerator",

    'summary': """
        A module to Create a Quality Quotation""",

    'description': """
        No Long Description
    """,

    'author': "Ty Cyr",
    'website': "R-E-A-L.iT",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.2',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    
    'installable': True,
    'auto_install': True
}
