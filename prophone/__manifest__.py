# -*- coding: utf-8 -*-
{
    "name": "ProPhone",
    "version": "17.0.1.0.0",
    "category": "Tools",
    "summary": "Store Quo (OpenPhone/Quo) call transcripts in Odoo",
    "license": "LGPL-3",
    "author": "Ézékiel deBlois",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizards/import_call_transcript_wizard_views.xml",
        "views/quo_call_views.xml",
        "views/res_partner_views.xml",
        "views/menus.xml",
        "data/ir_cron.xml",
    ],
    "application": True,
    "installable": True,
}
