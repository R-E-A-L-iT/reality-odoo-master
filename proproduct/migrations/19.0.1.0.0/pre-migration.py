# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

# Name of the inherited view that proproduct previously registered (now removed
# from the manifest during the Odoo 19 migration — see __manifest__.py and
# views/website_sale_product_renting.xml).
_STALE_VIEW_NAME = "Hide rental website elements unless enabled on product"


def migrate(cr, version):
    """Drop the stale 'rental hide' view left in the database.

    proproduct's views/website_sale_product_renting.xml inherited the Enterprise
    website_sale_renting.rental_product template with xpaths targeting pre-v19
    markup (//div[hasclass('js_main_product')]//t[@t-placeholder='select']/...).
    That view has been removed from the manifest for the v19 upgrade, but the
    record persists in the database from the previous install and is re-validated
    when proproduct's other product views load against the same parent — failing
    before Odoo's orphan cleanup runs. We delete it here (pre-load) so the
    registry can build. Re-add the view, re-anchored to the v19 rental markup,
    to restore the feature later.
    """
    if not version:
        # Fresh install: nothing stored to clean up.
        return

    cr.execute("SELECT id FROM ir_ui_view WHERE name = %s", (_STALE_VIEW_NAME,))
    view_ids = [row[0] for row in cr.fetchall()]
    if not view_ids:
        return

    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
        (tuple(view_ids),),
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
    _logger.info(
        "proproduct 19.0 migration: removed %d stale rental-hide view(s) "
        "incompatible with Odoo 19", len(view_ids),
    )
