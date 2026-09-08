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
    "version": "19.0.1.1.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "website",
        "stock_account",
        "product",
        "purchase",
        "stock",
        "portal",
        "website_sale",
        # Referenced by security/portal_document_rules.xml (account.model_account_move,
        # sale.model_sale_order). Both already arrive transitively via stock_account /
        # website_sale, but the ir.rule refs need them guaranteed loaded first.
        "account",
        "sale",
        "project",
        "mail",
    ],
    # always loaded
    "data": [
        "security/portal_document_rules.xml",
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
