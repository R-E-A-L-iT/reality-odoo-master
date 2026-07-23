# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

# proproduct website_sale product-page customizations that were disabled for the
# Odoo 19 upgrade (removed from the manifest — see __manifest__.py). Their records
# persist in the database from the previous install and get re-validated against
# the changed v19 core markup when proproduct's remaining views load, failing
# before Odoo's orphan cleanup runs. We drop them here, before load, targeting the
# module views *and* any website copy-on-write copies (which keep the same `key`).
_RETIRED_VIEW_KEYS = (
    "proproduct.website_sale_product_add_section",   # views/website_sale_product.xml
    "proproduct.rental_product_hide_unless_enabled",  # views/website_sale_product_renting.xml
    "proproduct.proproduct_website_sale_address_country_restrict",  # views/website_address.xml
    "proproduct.wishlist_page_add_to_cart",         # views/wishlist_page.xml (disabled for default store)
    "proproduct.website_sale_total_cart_only_override",  # views/website_cart.xml (disabled for default store)
)
_RETIRED_VIEW_NAMES = (
    "website_sale_product_add_section",
    "Hide rental website elements unless enabled on product",
    "proproduct_website_sale_address_country_restrict",
)


def migrate(cr, version):
    if not version:
        # Fresh install: nothing stored to clean up.
        return

    cr.execute(
        "SELECT id FROM ir_ui_view WHERE key IN %s OR name IN %s",
        (_RETIRED_VIEW_KEYS, _RETIRED_VIEW_NAMES),
    )
    view_ids = [row[0] for row in cr.fetchall()]
    if not view_ids:
        return

    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
        (tuple(view_ids),),
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
    _logger.info(
        "proproduct 19.0 migration: removed %d retired website_sale product "
        "view(s) incompatible with Odoo 19", len(view_ids),
    )
