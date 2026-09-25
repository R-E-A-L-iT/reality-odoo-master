# -*- coding: utf-8 -*-
{
    "name": "Upgrade Sync (Odoo 17 capture)",
    "summary": "Capture business actions in Odoo 17 so the Odoo 19 upgrade "
               "test instance can replay them.",
    "description": """
Odoo 17 SOURCE side of the Odoo 17 -> Odoo 19 upgrade-testing sync.

* Captures meaningful business actions (customer, opportunity, quotation,
  sent, confirm, cancel, invoice created/posted/cancelled/reversed, product)
  as ``upgrade.sync.event`` rows carrying a JSON business snapshot.
* Events are written in the SAME transaction as the business action (through a
  pre-commit hook), so a rolled-back action never leaves an orphan event.
* Capture errors are logged and never block the user.
* This module makes NO outbound calls. The Odoo 19 instance pulls events over
  JSON-RPC with a read-only technical user (group "Upgrade Sync Reader").

Capture is OFF by default (Settings > Technical > Upgrade Sync > Configuration).
    """,
    "author": "R-E-A-L.iT",
    "license": "LGPL-3",
    "category": "Hidden/Tools",
    "version": "17.0.1.0.0",
    "depends": [
        "sale_management",
        "crm",
        "account",
        "proquotes",
    ],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/upgrade_sync_event_views.xml",
        "views/res_config_settings_views.xml",
        "views/upgrade_sync_export_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
