{
    "name": "ProPortal",
    "summary": """
		Portal Upgrade Module that adds Advanced Features""",
    "description": """
		Module that allows expands Customer Portal
	""",
    "author": "Ezekiel deBlois, Ty Cyr",
    "license": "LGPL-3",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Sales",
    "version": "19.0.1.3",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "website",
        # account/payment/sale arrive transitively via stock_account and
        # website_sale, but views/portal_images.xml inherits views they own, so
        # declare them to guarantee they load before proportal.
        "account",
        "payment",
        "sale",
        "stock_account",
        "product",
        "purchase",
        "stock",
        "portal",
        "website_sale",
        "project",
        "mail",
    ],
    # always loaded
    "data": [
        "data/renewal_template.xml",
        "views/partnerView.xml",
        "views/stockView.xml",
        "views/productView.xml",
        "views/portal_images.xml",
        "views/partner_internal.xml",
        "views/productInstance.xml",
        "views/header_icons.xml",
        "views/backend_internal.xml",
        # "views/portal_companies_view.xml",
        "views/portal_product_view.xml",
        "views/portal_courses_view.xml",
    ],
}
