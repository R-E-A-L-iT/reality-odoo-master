# -*- coding: utf-8 -*-
{
    "name": "ProSync",
    "summary": """
        The ProSync module is a module developed for R-E-A-L.iT Solutions that allows Google Sheets
        to be used for bulk viewing/editing of data, which then gets imported into Odoo on a regular
        schedule to keep various sets of information up to date.""",
    "description": """
        The ProSync module is a module developed for R-E-A-L.iT Solutions that allows Google Sheets
        to be used for bulk viewing/editing of data, which then gets imported into Odoo on a regular
        schedule to keep various sets of information up to date.

        This applies to the following record types:
        - Product Templates [product.template records] (pricing info, images, purchase info, etc.)
        - Product Instances [stock.lot records] (individual tracking of owned products for ccps, renewal quotes, etc.)
        - Contacts (customers, vendors, etc.)
        And potentially more in the future.
    """,
    "author": "Ezekiel J. deBlois (Originally developed by Ty Cyr)",
    "license": "LGPL-3",
    "category": "Technical",
    "version": "2.0.0",
    "depends": [
        "base",
        "proportal",

        "product",
        "google_account",
        "proquotes",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/schedule.xml",
    ],
}
