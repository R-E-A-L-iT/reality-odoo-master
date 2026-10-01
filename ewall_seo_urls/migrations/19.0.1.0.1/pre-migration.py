# -*- coding: utf-8 -*-
"""Remove the SEO QWeb templates deleted from this module in the 19 port.

Their xpaths target pre-19 website_sale markup. Leaving the rows installed
makes the next module that touches the product page fail view validation.
"""
import logging

_logger = logging.getLogger(__name__)

_RETIRED_KEYS = (
    "ewall_seo_urls.product_inherit",
    "ewall_seo_urls.products_breadcrumb_inherit",
    "ewall_seo_urls.website_sale_filmstrip_categories",
    "ewall_seo_urls.products_attributes_inherits",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        """
        SELECT id
          FROM ir_ui_view
         WHERE key IN %s
            OR arch_db::text LIKE %s
        """,
        (_RETIRED_KEYS, "%breadcrumb p-0 mb-2 m-lg-0%"),
    )
    view_ids = [row[0] for row in cr.fetchall()]
    if not view_ids:
        return
    pending = set(view_ids)
    while pending:
        cr.execute(
            "SELECT id FROM ir_ui_view WHERE inherit_id IN %s AND id NOT IN %s",
            (tuple(pending), tuple(view_ids)),
        )
        extra = [row[0] for row in cr.fetchall()]
        if not extra:
            break
        view_ids.extend(extra)
        pending = set(extra)
    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
        (tuple(view_ids),),
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
    _logger.info(
        "ewall_seo_urls: removed %s retired website view(s)", len(view_ids)
    )
