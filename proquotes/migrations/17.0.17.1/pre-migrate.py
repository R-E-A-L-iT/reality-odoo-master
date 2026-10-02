# -*- coding: utf-8 -*-
"""Fill NULL required booleans so this upgrade can add NOT NULL.

is_optional, is_selected and is_quantityLocked are required with no default.
Odoo skips backfilling a boolean whose default is not True, then ALTER COLUMN
SET NOT NULL fails on the existing NULL rows. NULL already reads as False in
the ORM, so writing FALSE does not change what users see.

A column that is not there yet (fresh database, or an upgrade from before the
field existed) is skipped.
"""

_COLUMNS = ("is_optional", "is_selected", "is_quantityLocked")


def migrate(cr, version):
    cr.execute(
        """
        SELECT column_name
          FROM information_schema.columns
         WHERE table_schema = current_schema()
           AND table_name = 'sale_order_line'
           AND column_name IN %s
        """,
        (_COLUMNS,),
    )
    present = {row[0] for row in cr.fetchall()}
    for column in _COLUMNS:
        if column not in present:
            continue
        # Names are a fixed list. Quote them so the camel-case column is not
        # folded to lowercase.
        cr.execute(
            'UPDATE sale_order_line SET "%s" = FALSE WHERE "%s" IS NULL'
            % (column, column)
        )
