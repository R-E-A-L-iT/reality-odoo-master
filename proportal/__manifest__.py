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

    'version': '0.214',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website', 'stock_account', 'product', 'purchase', 'stock', 'portal', 'website_sale'],

    'assets': {
            'web.assets_frontend': [
                'proportal/static/src/CSS/customWebsiteStyle.css',
                'proportal/static/src/CSS/homepage.css',
                'proportal/static/src/CSS/calendar.css',
                'proportal/static/src/CSS/projectPortal.css',
                'proportal/static/src/CSS/productMiniMenu.css',
                'proportal/static/src/CSS/header.css',
                'proportal/static/src/CSS/footer.css',
                'proportal/static/src/CSS/mobileWebsite.css',
                'proportal/static/src/CSS/cart.css',
            ]
    },

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/web_base.xml',
        'views/partnerView.xml',
        # 'views/portalAccess.xml',
        'views/stockView.xml',
        'views/productView.xml',
        'views/customer_portal.xml',
        'views/portalProject.xml',
        'views/navButton.xml',
        'views/navbarCustom.xml',
        'views/cart.xml',
        'views/carousel.xml',
        'views/shopTile.xml',
        'views/language_selector.xml',
        'views/companyBackend.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
