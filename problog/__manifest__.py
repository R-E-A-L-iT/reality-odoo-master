
{
    'name': "ProBlog",

    'summary': """
        Styles and Structures Related to Blog
    """,

    'description': """
        Module That Improves the Style and Design of the Blog
	""",

    'author': "Ty Cyr",

    'license': "LGPL-3",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',

    'version': '0.5',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website'],

    'assets': {
            'web.assets_frontend': [
                'problog/static/css/blog.css'
            ]
    },

    # always loaded
    'data': [
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}