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
    ],
    'assets': {
        'web.assets_frontend': [
            'prowebsite/static/src/css/header_dropdowns.css',
            'prowebsite/static/src/css/three_product.css',
            'prowebsite/static/src/js/header_dropdowns.js',
            'prowebsite/static/src/js/three_product.js',
        ],
    }
}