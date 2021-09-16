# -*- coding: utf-8 -*-
{
    'name': "Apublisher",

    'summary': """
        Module for making pricelists language/region based""",

    'description': """
        Module for making pricelists language/region based
    """,

    'author': "ezeake",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Technical',

    'version': '0.2',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website', 'product', 'portal'],

    # always loaded
    'data': [
        'views/productView.xml',
    ],
}