# -*- coding: utf-8 -*-
{
    "name": "ProShipping",
    "version": "19.0.1.0.0",
    "category": "Operations/Inventory",
    "summary": "Sync Envio IoT packages into Odoo and display them in list/form views.",
    "description": """
Starter connector to pull package/shipment records from Envio IoT API and display them in Odoo.
You must configure the API Base URL and credentials in Settings, and adjust the endpoint/field mapping
to match your Envio dashboard API docs.
""",
    "author": "Ézékiel deBlois",
    "license": "LGPL-3",
    "depends": ["base", "stock", "base_setup", "web"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_config_settings_views.xml",
        "views/envio_menu_root.xml",
        "views/envio_package_views.xml",
        "views/envio_menu_items.xml",
        "views/envio_map_action.xml",
        "views/stock_lot_views.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "proshipping/static/src/js/envio_map_action.js",
            "proshipping/static/src/xml/envio_map_action.xml",
        ],
    },
    "application": True,
    "installable": True,
}
