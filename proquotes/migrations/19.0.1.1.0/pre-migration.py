# -*- coding: utf-8 -*-
#
# Removal of the custom per-line "selected" / optional-section system.
# ---------------------------------------------------------------------
# proquotes used to let customers pick/deselect quote lines and whole sections
# on the online quote (fields selected / sectionSelected / is_selected /
# demo_selected) and mark lines/sections optional or multiple-choice (optional /
# is_optional / special). Odoo 19's native optional sections replace all of that,
# so those fields have been removed from the models.
#
# This pre-migration, run before the updated models load, does two things:
#   1. Data: lines a customer had DESELECTED (selected='false') are set to
#      quantity 0 — kept visible so users can see and deal with them, but
#      contributing nothing to totals/delivery — instead of being deleted.
#      Hidden rental-kit component helper lines (x_is_rental_kit_component=True)
#      and section/note lines are left untouched. Affected orders' stored header
#      totals are recomputed from the remaining line amounts.
#   2. Schema: the removed columns are dropped. They were `required=True`, so
#      their NOT NULL constraints would otherwise break inserts of new
#      sale.order.line / sale.order.template.line rows that no longer supply them.

import logging

_logger = logging.getLogger(__name__)

# Removed stored columns, per table. (demo_selected was a non-stored compute, so
# it has no column and is not listed.)
_REMOVED_COLUMNS = {
    "sale_order_line": (
        "selected", "sectionSelected", "is_selected",
        "optional", "is_optional", "special",
    ),
    "sale_order_template_line": (
        "selected", "sectionSelected", "optional", "special",
    ),
}


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version:
        # Fresh install: the removed fields never existed, nothing to do.
        return

    _zero_out_deselected_lines(cr)
    _drop_removed_columns(cr)


def _zero_out_deselected_lines(cr):
    if not _column_exists(cr, "sale_order_line", "selected"):
        return  # already migrated

    has_component = _column_exists(cr, "sale_order_line", "x_is_rental_kit_component")
    zero_guard = (
        "AND COALESCE(x_is_rental_kit_component, false) = false" if has_component else ""
    )

    # Orders that own at least one customer-deselected line (captured before the
    # update so their header totals can be recomputed afterwards).
    cr.execute(
        "SELECT DISTINCT order_id FROM sale_order_line "
        " WHERE selected = 'false' AND display_type IS NULL " + zero_guard
    )
    order_ids = tuple(r[0] for r in cr.fetchall() if r[0])

    # 1) Zero the quantity + stored amounts on the deselected lines.
    cr.execute(
        "UPDATE sale_order_line "
        "   SET product_uom_qty = 0, price_subtotal = 0, price_total = 0, price_tax = 0 "
        " WHERE selected = 'false' AND display_type IS NULL " + zero_guard
    )
    zeroed = cr.rowcount

    # 2) Recompute affected orders' stored header totals from the remaining lines
    #    (matching the model's _amount_all: real product lines only, components
    #    and section/note lines excluded).
    if order_ids:
        sum_guard = (
            "AND COALESCE(l.x_is_rental_kit_component, false) = false" if has_component else ""
        )
        cr.execute(
            """
            UPDATE sale_order o
               SET amount_untaxed = COALESCE(s.untaxed, 0.0),
                   amount_tax     = COALESCE(s.tax, 0.0),
                   amount_total   = COALESCE(s.untaxed, 0.0) + COALESCE(s.tax, 0.0)
              FROM (
                    SELECT l.order_id,
                           SUM(l.price_subtotal) AS untaxed,
                           SUM(l.price_tax)      AS tax
                      FROM sale_order_line l
                     WHERE l.display_type IS NULL {sum_guard}
                     GROUP BY l.order_id
                   ) s
             WHERE o.id = s.order_id AND o.id IN %s
            """.format(sum_guard=sum_guard),
            (order_ids,),
        )

    _logger.info(
        "proquotes 19.0.1.1.0 migration: zeroed %d customer-deselected line(s) "
        "across %d order(s) (custom 'selected' system removed)",
        zeroed, len(order_ids),
    )


def _drop_removed_columns(cr):
    for table, columns in _REMOVED_COLUMNS.items():
        for column in columns:
            if _column_exists(cr, table, column):
                cr.execute(
                    'ALTER TABLE "%s" DROP COLUMN IF EXISTS "%s"' % (table, column)
                )
    _logger.info(
        "proquotes 19.0.1.1.0 migration: dropped obsolete selected/optional columns"
    )
