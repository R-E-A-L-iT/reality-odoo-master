# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

# Stale ir.ui.view records that persist from the previous install and get
# re-validated against v19's changed core markup when proquotes' views load,
# failing before Odoo's orphan cleanup runs. We drop them here, before load,
# targeting the module views AND any website copy-on-write copies (same `key`).
#
# Two kinds are listed:
#   1. Views whose source file is still disabled (retired until rebuilt).
#   2. quote_preview.xml's templates — that file has been RE-ENABLED and
#      re-anchored to v19, but its old arch survives in the DB as a website COW
#      copy which the module update does NOT rewrite (COW copies have no
#      ir_model_data link), so it kept failing on the removed
#      //div[@id="quote_content"]//b[1] xpath. Deleting them here (pre-load)
#      purges the stale arch; the module's data load then recreates them fresh
#      from the re-anchored file.
_RETIRED_VIEW_KEYS = (
    # views/Quote/quote_preview.xml — purged so the re-anchored file recreates them
    "proquotes.sale_order_total",
    "proquotes.address_card_tile",
    "proquotes.quote_hero_quicknav",
    "proquotes.quote_terms_acceptance",
    "proquotes.sale_order_portal_content",
    "proquotes.ba_sale_order_portal_template",
    "proquotes.portal_footer",
    # views/Invoice/follow_up_email.xml (Enterprise account_followup report override)
    "proquotes.template_followup_report_custom",
    # views/Other/tax.xml (inherits removed account.tax_groups_totals + standalone content)
    "proquotes.proquote_tax_display",
    "proquotes.tax_group_name_content",
    # views/Other/mail.xml (removed a row from mail.mail_notification_light)
    "proquotes.ba_remove_power_override_second_tr",
    # views/Other/quoteEmailFooter.xml (inherited layout override coupled to Other/mail.xml)
    "proquotes.mail_notification_layout_inherit",
)


def migrate(cr, version):
    if not version:
        # Fresh install: nothing stored to clean up.
        return

    cr.execute("SELECT id FROM ir_ui_view WHERE key IN %s", (_RETIRED_VIEW_KEYS,))
    view_ids = [row[0] for row in cr.fetchall()]
    if not view_ids:
        return

    cr.execute(
        "DELETE FROM ir_model_data WHERE model = 'ir.ui.view' AND res_id IN %s",
        (tuple(view_ids),),
    )
    cr.execute("DELETE FROM ir_ui_view WHERE id IN %s", (tuple(view_ids),))
    _logger.info(
        "proquotes 19.0 migration: removed %d stale quote_preview view(s) "
        "incompatible with Odoo 19", len(view_ids),
    )

    _cleanup_broken_chatter_position_patch(cr)


def _cleanup_broken_chatter_position_patch(cr):
    """Safety net so the backend can render even if web_chatter_position_cr's
    model isn't loaded.

    That module patches web.webclient_bootstrap to emit
    `request.env.user.chatter_position`. If its res.users field isn't registered
    (module not (re)loaded on the v19 upgrade), rendering the web client raises
    AttributeError and the whole backend is unreachable. When the column is
    absent, drop the stale inheriting view; if the module does load, it recreates
    a (now defensive) patch itself and this is a no-op.
    """
    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'res_users' AND column_name = 'chatter_position'
    """)
    if cr.fetchone():
        return  # field exists -> patch is safe, leave it alone

    cr.execute("""
        DELETE FROM ir_ui_view
         WHERE arch_db::text LIKE '%chatter_position%'
           AND inherit_id IN (
               SELECT res_id FROM ir_model_data
                WHERE module = 'web' AND name = 'webclient_bootstrap'
           )
    """)
    if cr.rowcount:
        _logger.warning(
            "proquotes 19.0 migration: removed %d stale webclient_bootstrap "
            "chatter_position patch view(s) (field not present)", cr.rowcount,
        )
