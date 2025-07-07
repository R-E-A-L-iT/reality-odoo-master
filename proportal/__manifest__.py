{
    "name": "ProPortal",
    "summary": """
		Portal Upgrade Module that adds Advanced Features""",
    "description": """Features added by this module:
        1. Integrated Company and Employee portals
        2. More documents available in portal
        3. Small website updates
        4. etc...
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
    ],
    "data": [
        "views/web_base.xml",
        "views/partnerView.xml",
        "views/stockView.xml",
        "views/productView.xml",
        "views/customer_portal.xml",
        "views/portalProject.xml",
        "views/partner_internal.xml",
        "views/productInstance.xml",
        "views/header_icons.xml",
        "views/backend_internal.xml",
    ],
}
