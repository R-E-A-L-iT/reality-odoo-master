{
    'name': "ProPortal",

    'summary': """
        Portal Upgrade Module that adds Advanced Features""",

    'description': """
        Module that allows expands Customer Portal
    """,

    'author': "Ty Cyr",
    
    'license': "LGPL-3",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',
    'version': '0.5',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website', 'stock_account', 'product', 'purchase', 'stock', 'portal'],
    
    'assets': {
        'web.assets_frontend': [
            'proportal/static/src/CSS/projectPortal.css'
        ]
    },
    
    # always loaded
    'data': [
        #'security/ir.model.access.csv',
        'views/partnerView.xml',
        #'views/portalAccess.xml',
        'views/productView.xml',
        'views/stockView.xml',
        'views/customer_portal.xml',
        'views/portalProject.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}