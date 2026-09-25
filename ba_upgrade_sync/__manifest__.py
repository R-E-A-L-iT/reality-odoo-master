# -*- coding: utf-8 -*-
{
    "name": "Upgrade Sync (Odoo 19 replay)",
    "summary": "Pull business events captured in Odoo 17 and replay them through "
               "the Odoo 19 business methods for upgrade testing.",
    "description": """
Odoo 19 TARGET side of the Odoo 17 -> Odoo 19 upgrade-testing sync.
Install on the upgrade test / staging database (OriginCopy) only.

* Pulls ``upgrade.sync.event`` rows from Odoo 17 over HTTPS JSON-RPC with a
  read-only API key (Odoo 17 never calls out).
* Resolves Odoo 17 records to Odoo 19 records through a mapping table, the same
  id checked by fingerprint (upgraded database copy) or business keys. Master
  data (taxes, journals, accounts, pricelists, ...) is never created .
* Transforms Odoo 17 payloads (renamed fields, proquotes optional / multiple
  sections -> Odoo 19 optional / single-choice sections, product types, ...).
* Replays the business action with the Odoo 19 ORM methods (action_confirm,
  _create_invoices, action_post, ...) so Odoo 19 + custom module logic runs.
* Idempotent (unique event UUID + mappings), ordered per business document,
  bounded retries, dry-run mode, Odoo 17 vs Odoo 19 business comparison.

Auto sync is OFF and dry run is ON by default.
    """,
    "author": "R-E-A-L.iT",
    "license": "LGPL-3",
    "category": "Hidden/Tools",
    "version": "19.0.1.0.0",
    "depends": [
        "sale_management",
        "crm",
        "account",
        "proquotes",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/config_data.xml",
        "data/cron.xml",
        "views/upgrade_sync_event_views.xml",
        "views/upgrade_sync_mapping_views.xml",
        "views/upgrade_sync_config_views.xml",
        "views/upgrade_sync_import_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
