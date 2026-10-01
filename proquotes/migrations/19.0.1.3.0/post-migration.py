# -*- coding: utf-8 -*-
"""The data file has loaded. Make sure the three footer inherits exist and are on."""

import logging

_logger = logging.getLogger(__name__)

_REQUIRED = (
    "custom_footer_boxed",
    "custom_footer_striped",
    "custom_footer_bold",
)


def migrate(cr, version):
    if not version:
        return

    cr.execute(
        """
        UPDATE ir_ui_view
           SET active = true
         WHERE id IN (
                SELECT res_id
                  FROM ir_model_data
                 WHERE module = 'proquotes'
                   AND name IN %s
                   AND model = 'ir.ui.view'
              )
        """,
        (_REQUIRED,),
    )
    cr.execute(
        """
        SELECT t.name
          FROM (VALUES ('custom_footer_boxed'),
                       ('custom_footer_striped'),
                       ('custom_footer_bold')) AS t(name)
         WHERE NOT EXISTS (
                SELECT 1
                  FROM ir_model_data d
                  JOIN ir_ui_view v ON v.id = d.res_id
                 WHERE d.module = 'proquotes'
                   AND d.name = t.name
                   AND d.model = 'ir.ui.view'
                   AND v.active
              )
        """
    )
    missing = [row[0] for row in cr.fetchall()]
    if missing:
        raise RuntimeError(
            "proquotes footer views were not created: %s" % ", ".join(missing)
        )
    _logger.info("proquotes 19.0.1.3.0: footer layout views are active")
