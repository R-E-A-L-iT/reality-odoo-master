# -*- coding: utf-8 -*-
{
    "name": "Pro Upgrade Testkit",
    "summary": "Rebuild a deterministic Enginelly-tagged sales/rental suite for Odoo 19 upgrade testing.",
    "description": """
OriginCopy / staging only. Never install on production.

Provides a backend wizard **Rebuild Enginelly test suite** that idempotently
cancels prior Enginelly-tagged documents and recreates a known set of quotes,
orders, invoices, and rental flows via ORM so upgrade results are comparable
run-to-run.
    """,
    "author": "R-E-A-L.iT",
    "license": "LGPL-3",
    "category": "Sales",
    "version": "19.0.1.0.0",
    "depends": [
        "mail",
        "sale_management",
        "sale_renting",
        "stock",
        "account",
        "proquotes",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/test_run_views.xml",
        "wizard/rebuild_wizard_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
