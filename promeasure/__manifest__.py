{
    "name": "ProMeasure",
    "summary": """
		Portal Upgrade Module that adds Advanced Features""",
    "description": """
		Module that expands website visitor and crm reveal data records
	""",
    "author": "Joshua Brodie",
    "license": "LGPL-3",
    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    "category": "Sales",
    "version": "17.0",
    # any module necessary for this one to work correctly
    "depends": [
        "base",
        "website",
        'website_sale',
        "crm",
        'website_crm_iap_reveal'
    ],
    # always loaded
    "data": [
        "views/website_visitor_views.xml"
    ],
    'installable': True,
    'application': False
}