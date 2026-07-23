# -*- coding: utf-8 -*-
{
    "name": "ProWebsite",
    "summary": """
        Helper module to add website features""",
    "description": """
        Helper module to add website features
    """,
    "author": "Ézékiel deBlois",
    "license": "LGPL-3",
    "category": "Technical",
    "version": "19.0.1.0.0",
    'application': True,
    "depends": [
        "base",
        "website_sale",
        "crm",
    ],
    'assets': {
        'web.assets_frontend': [
            'prowebsite/static/src/css/header_dropdowns.css',
            # three_product.css is the broad custom stylesheet (site header, hero/landing
            # sections, and the "notify me" new-product signup styling shown on the home
            # page). Kept ENABLED — it targets custom classes/snippets, not the default
            # shop/product pages, so it doesn't un-default the store.
            'prowebsite/static/src/css/three_product.css',
            'prowebsite/static/src/css/rtc_series.css',
            'prowebsite/static/src/css/rtc_series_sections.css',
            'prowebsite/static/src/css/rtc_demo_request.css',
            'prowebsite/static/src/js/header_dropdowns.js',
            'prowebsite/static/src/js/rtc_series.js',
            'prowebsite/static/src/js/rtc_scroll_model.js',
            'prowebsite/static/src/js/rtc_demo_request.js',
            # Odoo 19 migration: store shop/product-PAGE customizations disabled to
            # show the default shop/product pages (3D product viewer + shop/product CSS
            # that restyles the standard pages). Re-enable when porting the store.
            # 'prowebsite/static/src/css/product_page.css',
            # 'prowebsite/static/src/css/shop_page.css',
            # 'prowebsite/static/src/css/multimapper.css',
            # 'prowebsite/static/src/js/three_product.js',
            # 'prowebsite/static/src/js/product_page.js',
            # 'prowebsite/static/src/js/multimapper.js',
        ],
    }
}