# -*- coding: utf-8 -*-
{
    "name": "ProQuotes Address Selector",
    "summary": "Replace quote portal address forms with clickable address card picker.",
    "author": "Brainecrew Apps",
    "license": "LGPL-3",
    "category": "Sales",
    "version": "17.0",
    "depends": ["proquotes"],
    "assets": {
        "web.assets_frontend": [
            "proquotes_address_selector/static/src/css/address_selector.css",
            "proquotes_address_selector/static/src/js/address_selector.js",
        ],
        "web.assets_common": [
            "proquotes_address_selector/static/src/css/address_selector.css",
            "proquotes_address_selector/static/src/js/address_selector.js",
        ],
    },
    "data": [
        "views/quote_address_selector.xml",
    ],
}
