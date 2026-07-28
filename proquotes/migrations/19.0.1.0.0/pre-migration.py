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
    _migrate_header_footer_to_quotation_document(cr)


def _table_exists(cr, table):
    cr.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s", (table,)
    )
    return bool(cr.fetchone())


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def _drop_foreign_keys(cr, table, column):
    """Drop every FK constraint enforced on <table>.<column> (regardless of name)."""
    cr.execute(
        """
        SELECT c.conname
          FROM pg_constraint c
          JOIN pg_class t ON t.oid = c.conrelid
          JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY (c.conkey)
         WHERE t.relname = %s AND a.attname = %s AND c.contype = 'f'
        """,
        (table, column),
    )
    for (conname,) in cr.fetchall():
        cr.execute('ALTER TABLE "%s" DROP CONSTRAINT IF EXISTS "%s"' % (table, conname))


# Columns that used to be Many2one("header.footer") and are now
# Many2one("quotation.document"). Their stored ids point at the legacy
# header_footer rows and must be remapped to the migrated quotation_document rows.
_HF_FK_COLUMNS = (
    ("sale_order", "header_id"),
    ("sale_order", "footer_id"),
    ("res_company", "default_footer_id"),
    ("res_users_company_footer", "footer_id"),
    ("sale_order_template", "header_id"),
    ("account_move", "footer_id"),
    ("purchase_order", "footer_id"),
    ("stock_picking", "footer_id"),
    ("helpdesk_ticket", "footer_id"),
)

# Legacy view / action xml ids from the old header.footer management screen.
_HF_LEGACY_UI = {
    "ir_ui_view": ("header_footer_tree", "header_footer_form"),
    "ir_act_window": ("header_footer_window",),
    "ir_act_window_view": ("header_footer_window_tree", "header_footer_window_form"),
}
_HF_LEGACY_UI_MODELS = {
    "ir_ui_view": "ir.ui.view",
    "ir_act_window": "ir.actions.act_window",
    "ir_act_window_view": "ir.actions.act_window.view",
}


def _migrate_header_footer_to_quotation_document(cr):
    """Merge the legacy custom ``header.footer`` model into the native
    ``quotation.document`` model (sale_pdf_quote_builder) as a new "preview"
    document class.

    Runs before proquotes' models load, so that when Odoo reconciles the FK on
    the (now retargeted) header_id/footer_id columns it finds valid
    quotation_document ids instead of orphan header_footer ids.
    """
    if not _table_exists(cr, "header_footer"):
        return  # already migrated or never existed
    if not _table_exists(cr, "quotation_document"):
        _logger.warning(
            "proquotes 19.0 migration: quotation_document table missing; "
            "cannot merge header.footer (is sale_pdf_quote_builder installed?)"
        )
        return

    # 1. Helper columns on quotation_document (added by the model later, but we
    #    need them now for the raw inserts) + the company scoping m2m rel table.
    cr.execute("ALTER TABLE quotation_document ADD COLUMN IF NOT EXISTS doc_class varchar")
    cr.execute("ALTER TABLE quotation_document ADD COLUMN IF NOT EXISTS url varchar")
    cr.execute("ALTER TABLE quotation_document ADD COLUMN IF NOT EXISTS legacy_hf_id integer")
    cr.execute(
        """
        CREATE TABLE IF NOT EXISTS quotation_document_res_company_rel (
            quotation_document_id integer NOT NULL,
            res_company_id integer NOT NULL,
            PRIMARY KEY (quotation_document_id, res_company_id)
        )
        """
    )
    # Existing native documents are "report" documents.
    cr.execute("UPDATE quotation_document SET doc_class = 'report' WHERE doc_class IS NULL")

    # 2. Create an ir.attachment + quotation_document (preview) per header.footer.
    hf_active = "COALESCE(active, true)" if _column_exists(cr, "header_footer", "active") else "true"
    cr.execute(
        "SELECT id, name, record_type, url, %s FROM header_footer" % hf_active
    )
    count = 0
    for hf_id, name, record_type, url, active in cr.fetchall():
        doctype = "header" if (record_type or "").lower() == "header" else "footer"
        cr.execute(
            """
            INSERT INTO ir_attachment
                (name, type, res_model, create_uid, create_date, write_uid, write_date)
            VALUES (%s, 'binary', 'quotation.document', 1, now(), 1, now())
            RETURNING id
            """,
            (name or url or "Header/Footer",),
        )
        att_id = cr.fetchone()[0]
        cr.execute(
            """
            INSERT INTO quotation_document
                (ir_attachment_id, document_type, active, sequence, doc_class, url,
                 legacy_hf_id, create_uid, create_date, write_uid, write_date)
            VALUES (%s, %s, %s, 10, 'preview', %s, %s, 1, now(), 1, now())
            RETURNING id
            """,
            (att_id, doctype, bool(active), url, hf_id),
        )
        qd_id = cr.fetchone()[0]
        cr.execute("UPDATE ir_attachment SET res_id = %s WHERE id = %s", (qd_id, att_id))
        count += 1

    # 3. Carry over per-company scoping.
    if _table_exists(cr, "header_footer_res_company_rel"):
        cr.execute(
            """
            INSERT INTO quotation_document_res_company_rel
                (quotation_document_id, res_company_id)
            SELECT qd.id, rel.res_company_id
              FROM header_footer_res_company_rel rel
              JOIN quotation_document qd ON qd.legacy_hf_id = rel.header_footer_id
            ON CONFLICT DO NOTHING
            """
        )

    # 4. Remap every FK column from the legacy id to the migrated document id.
    for table, column in _HF_FK_COLUMNS:
        if not _table_exists(cr, table) or not _column_exists(cr, table, column):
            continue
        _drop_foreign_keys(cr, table, column)
        cr.execute(
            'UPDATE "%s" t SET "%s" = qd.id '
            "  FROM quotation_document qd "
            ' WHERE qd.legacy_hf_id = t."%s"' % (table, column, column)
        )

    # 5. Repoint the seed xml ids (proquotes.footer_canada, ...) to the new records
    #    so the data files update them in place instead of creating duplicates.
    cr.execute(
        """
        UPDATE ir_model_data d
           SET model = 'quotation.document', res_id = qd.id
          FROM quotation_document qd
         WHERE d.model = 'header.footer'
           AND qd.legacy_hf_id = d.res_id
        """
    )

    # 6. Remove the legacy management views/actions (retired from the XML).
    for table, names in _HF_LEGACY_UI.items():
        if not _table_exists(cr, table):
            continue
        model = _HF_LEGACY_UI_MODELS[table]
        cr.execute(
            'DELETE FROM "%s" WHERE id IN ('
            "  SELECT res_id FROM ir_model_data "
            "   WHERE module = 'proquotes' AND model = %%s AND name IN %%s)" % table,
            (model, names),
        )
        cr.execute(
            "DELETE FROM ir_model_data "
            " WHERE module = 'proquotes' AND model = %s AND name IN %s",
            (model, names),
        )

    # 7. Drop the legacy table + helper column. Odoo's orphan cleanup will remove
    #    the leftover header.footer model metadata when proquotes finishes loading.
    cr.execute("ALTER TABLE quotation_document DROP COLUMN IF EXISTS legacy_hf_id")
    cr.execute("DROP TABLE IF EXISTS header_footer_res_company_rel")
    cr.execute("DROP TABLE IF EXISTS header_footer CASCADE")

    _logger.info(
        "proquotes 19.0 migration: merged %d header.footer record(s) into "
        "quotation.document (preview class)", count,
    )


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
