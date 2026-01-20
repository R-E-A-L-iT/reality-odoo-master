{
    "name": "ProPortal",
    "summary": """
		Portal Upgrade Module that adds Advanced Features""",
    "description": """
		Module that allows expands Customer Portal
	""",
    "author": "Ezekiel deBlois, Ty Cyr",
    "license": "LGPL-3",
    "category": "Sales",
    "version": "17.0",
    "depends": [
        "base",
        "website",
        "stock_account",
        "product",
        "purchase",
        "stock",
        "portal",
        "website_sale",
        "project",
        "mail",
    ],
    "data": [
        "data/renewal_template.xml",
        "views/partnerView.xml",
        "views/stockView.xml",
        "views/productView.xml",
        "views/partner_internal.xml",
        "views/productInstance.xml",
        "views/header_icons.xml",
        "views/backend_internal.xml",
        "views/portal_companies_view.xml",
        "views/portal_product_view.xml",
        "views/portal_courses_view.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "proportal/static/src/css/portal_company.css",
            "proportal/static/src/js/portal_company.js",
        ],
    },
}
