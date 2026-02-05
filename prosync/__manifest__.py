# -*- coding: utf-8 -*-
{
    "name": "ProSync",
    "summary": """
        Module that manages the syncing between Odoo and Google Sheets""",
    "description": """
        Module that manages the syncing between Odoo and Google Sheets
    """,
    "author": "Ezekiel deBlois",
    "license": "LGPL-3",
    "category": "Technical",
    "version": "0.2",
    'application': True,
    "depends": [
        "base",
        "proportal",
        "product",
        "mrp",
        "google_account",
        "proquotes",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/schedule.xml",
        "data/run_sync_action.xml",
        "views/res_partner.xml",
        "views/stock_lot.xml",
        "views/module_views.xml",
        "views/product_template.xml",
    ],
}