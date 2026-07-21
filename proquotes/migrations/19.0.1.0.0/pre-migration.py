# -*- coding: utf-8 -*-
import logging

_logger = logging.getLogger(__name__)

# Templates defined in proquotes/views/Quote/quote_preview.xml, which was disabled
# for the Odoo 19 upgrade (its xpaths inherit sale/portal templates reworked in v19
# — see __manifest__.py). Their ir.ui.view records persist from the previous install
# and get re-validated against the changed core markup when proquotes' views load,
# failing before Odoo's orphan cleanup runs. We drop them here, before load,
# targeting the module views and any website copy-on-write copies (same `key`).
_RETIRED_VIEW_KEYS = (
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
