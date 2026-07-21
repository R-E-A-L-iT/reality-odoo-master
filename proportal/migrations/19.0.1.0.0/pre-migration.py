# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Remove a stale website customization of the portal language selector.

    A website-editor copy (copy-on-write) of proportal's globe language-selector
    override was stored in the database with a pre-Odoo-19 arch that xpaths on
    ``//*[contains(@t-attf-class, 'dropdown-toggle')]``. After proportal replaces
    the language-selector ``<button>`` (which in v19 now carries a plain ``class``
    rather than a ``t-attf-class``), that element can no longer be located, so the
    stored view fails validation and prevents the v19 registry from loading.

    The view is not defined in any module file (name ``language_selector_inline``),
    so it is safe to drop it here — before proportal's own views are loaded — along
    with any dangling external id. proportal recreates its clean globe override
    from ``views/header_icons.xml``.
    """
    if not version:
        # Fresh install: nothing stored to clean up.
        return

    cr.execute("""
        SELECT id
          FROM ir_ui_view
         WHERE name = 'language_selector_inline'
    """)
    view_ids = [row[0] for row in cr.fetchall()]
    if not view_ids:
        return

    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
        (tuple(view_ids),),
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
    _logger.info(
        "proportal 19.0 migration: removed %d stale language-selector view(s) "
        "incompatible with Odoo 19", len(view_ids),
    )
