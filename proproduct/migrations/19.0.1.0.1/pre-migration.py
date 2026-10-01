# -*- coding: utf-8 -*-
"""Drop website QWeb inherits whose xpaths no longer match Odoo 19.

`ewall_seo_urls.product_inherit` (name "Product") still sits in upgraded
databases after its XML file was removed. It anchors

    //ol[@class='breadcrumb p-0 mb-2 m-lg-0']/li[@class='breadcrumb-item']

which the v19 product page does not have. Loading proproduct's product
template re-validates that sibling inherit and the registry dies before
Odoo gets to orphan cleanup. The same is true of the other SEO templates
removed in the same port.
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
    # Website copies and anything still inheriting these rows.
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
        "proproduct: removed %s Odoo 19-incompatible website view(s)", len(view_ids)
    )
