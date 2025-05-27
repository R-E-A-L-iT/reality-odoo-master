{
    "name": "ProProduct",
    "summary": "A module developed for R-E-A-L.iT Solutions to enhance products.",
    "description": """This module adds product bundles to odoo, which can have their subproducts and quantities independently of the parent.""",
    "author": "Ezekiel deBlois",
    "license": "LGPL-3",
    "version": "17.0",
    "depends": ["base", "sale"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_bundle.xml",
        "views/product_bundle_wizard.xml",
        "views/product_bundle_instance.xml",
        "views/views.xml",
    ],
    "installable": True,
    "application": True,
}
