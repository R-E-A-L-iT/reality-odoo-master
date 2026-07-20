# -*- coding: utf-8 -*-
{
    "name": "ProPhone",
    "version": "19.0.1.0.0",
    "category": "Tools",
    "summary": "Store Quo (OpenPhone/Quo) call transcripts in Odoo",
    "license": "LGPL-3",
    "author": "Ézékiel deBlois",
    "depends": [
        "base",
        "sale",
        "mail",
        "contacts",
        "crm",
        "sale_management",
        ],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "wizards/import_call_transcript_wizard_views.xml",
        "views/quo_call_views.xml",
        "views/res_partner_views.xml",
        "views/quo_ignored_contacts_views.xml",
        "views/res_users_view.xml",
        "views/quo_send_text_wizard_views.xml",
        "views/menus.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "prophone/static/src/js/chatter_send_text_patch.js",
            "prophone/static/src/xml/chatter_send_text.xml",
        ],
    },
    "application": True,
    "installable": True,
}
