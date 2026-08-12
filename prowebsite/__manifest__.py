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
    "version": "0.1",
    'application': True,
    "depends": [
        "base",
        "website_sale",
        "crm",
    ],
    'assets': {
        'web.assets_frontend': [
            'prowebsite/static/src/css/header_dropdowns.css',
            'prowebsite/static/src/css/three_product.css',
            'prowebsite/static/src/css/rtc_series.css',
            'prowebsite/static/src/css/rtc_series_sections.css',
            'prowebsite/static/src/css/product_sections.css',
            'prowebsite/static/src/css/product_page.css',
            'prowebsite/static/src/css/shop_page.css',
            'prowebsite/static/src/css/multimapper.css',
            'prowebsite/static/src/css/rtc_demo_request.css',
            'prowebsite/static/src/css/product_lead.css',
            'prowebsite/static/src/js/header_dropdowns.js',
            'prowebsite/static/src/js/three_product.js',
            'prowebsite/static/src/js/rtc_series.js',
            'prowebsite/static/src/js/rtc_scroll_model.js',
            'prowebsite/static/src/js/product_page.js',
            'prowebsite/static/src/js/multimapper.js',
            'prowebsite/static/src/js/rtc_demo_request.js',
            'prowebsite/static/src/js/tradeshow_signup.js',
            'prowebsite/static/src/js/product_lead.js',
        ],
    }
}