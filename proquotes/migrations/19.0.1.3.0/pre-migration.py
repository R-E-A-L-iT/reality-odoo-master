# -*- coding: utf-8 -*-
"""Recreate the Striped and Bold quote footer views on an upgraded database.

The 17-to-19 upgrade loaded proquotes 19.0.1.2.0 while
``custom_footer_striped`` and ``custom_footer_bold`` were commented out of
``report_footer.xml`` (their v17 xpaths targeted ``o_background_footer`` and
``o_clean_footer``, classes Odoo 19 removed). ``_process_end`` then dropped
the non-noupdate xmlids. Boxed stayed: its v17 path ``/t/div[3]/div/div``
still matches the third div of ``web.external_layout_boxed``, so that inherit
kept replacing the footer.

Putting the templates back without a version bump does not reload the module
on odoo.sh. A later ``-u`` also fails to create them when the upgrade left the
old view row behind without its xmlid (a website copy-on-write copy, or a view
whose ``ir.model.data`` was removed). That row still inherits the layout with
the dead xpath, so validating the new template raises "cannot be located in
parent view" and the whole file rolls back. A dangling noupdate xmlid alone
does not block creation; Odoo drops it and inserts the view. This script
removes the leftovers before the data file loads, including rows whose
``res_id`` no longer points at a view.
"""

import logging

_logger = logging.getLogger(__name__)

# Generic views and website COW copies share these keys.
_RESET_KEYS = (
    "proquotes.custom_footer_striped",
    "proquotes.custom_footer_bold",
    # Debug-only snippet (Test5/Test6). Nothing calls it anymore.
    "proquotes.custom_footer_image_block",
)
_XML_NAMES = (
    "custom_footer_striped",
    "custom_footer_bold",
    "custom_footer_image_block",
)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        SELECT v.id
          FROM ir_ui_view v
          JOIN ir_ui_view parent ON parent.id = v.inherit_id
         WHERE parent.key IN ('web.external_layout_striped', 'web.external_layout_bold')
           AND (v.arch_db::text LIKE %s OR v.arch_db::text LIKE %s)
        """,
        ("%o_background_footer%", "%o_clean_footer%"),
    )
    view_ids = {row[0] for row in cr.fetchall()}

    cr.execute("SELECT id FROM ir_ui_view WHERE key IN %s", (_RESET_KEYS,))
    view_ids.update(row[0] for row in cr.fetchall())

    if view_ids:
        ids = tuple(view_ids)
        # Drop children first so inherit_id FKs do not block the delete.
        cr.execute(
            "SELECT id FROM ir_ui_view WHERE inherit_id IN %s AND id NOT IN %s",
            (ids, ids),
        )
        child_ids = tuple(row[0] for row in cr.fetchall())
        if child_ids:
            cr.execute(
                "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
                (child_ids,),
            )
            cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (child_ids,))
        cr.execute(
            "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
            (ids,),
        )
        cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (ids,))

    # Dangling or noupdate xmlids whose view row is already gone. _process_end
    # keeps noupdate rows, and a NULL res_id is not in its cleanup query.
    cr.execute(
        """
        DELETE FROM ir_model_data
         WHERE module = 'proquotes'
           AND name IN %s
           AND model = 'ir.ui.view'
        """,
        (_XML_NAMES,),
    )

    # Boxed still works, but a noupdate flag would keep the v17 arch forever.
    cr.execute(
        """
        UPDATE ir_model_data
           SET noupdate = false
         WHERE module = 'proquotes'
           AND name = 'custom_footer_boxed'
           AND model = 'ir.ui.view'
        """
    )

    _logger.info(
        "proquotes 19.0.1.3.0: removed %d stale footer view(s) so striped/bold can load",
        len(view_ids),
    )
