# -*- coding: utf-8 -*-
{
    "name": "ProQuotes",
    "summary": """Module that adds features to Quotes, Invoices, Purchases, and Deliveries.""",
    "description": """This module adds renewal quote features, multiple choice/selection options for clients, a variety of new fields, and better user interface.""",
    "author": "Ézékiel deBlois",
    "license": "LGPL-3",
    "category": "Sales",
    "depends": [
        "sale_stock",
        "base",
        "web",
        "mail",
        "mail_group",
        "account",
        "proportal",
        "stock",
        "website",
        "sale_management",
        "sale_pdf_quote_builder",
        "sale",
        "hr",
        "digest",
        "portal",
        "contacts",
        "stock_account",
        "project",
        "sale_project",
        "website_sale",
        "sale_timesheet",
        "purchase",
        "crm",
        "website_crm",
        "sale_renting",
    ],
    "assets": {
        # NOTE: web.assets_common was removed in Odoo 18/19. Its entries were
        # merged below: frontend-facing CSS into web.assets_frontend and
        # backend.css into web.assets_backend. The JS it declared (fold, rental,
        # poNumber, website_preview, ccp_selection) was already duplicated in the
        # frontend/backend bundles, so nothing new was added there.
        'web.assets_frontend': [
            # migrated from web.assets_common:
            "proquotes/static/src/CSS/foldProducts.css",
            "proquotes/static/src/CSS/pdf.css",
            "proquotes/static/src/CSS/user-info.css",
            "proquotes/static/src/CSS/quoteStyle.css",
            "proquotes/static/src/CSS/quoteHeaderText.css",
            # "proquotes/static/src/CSS/rental_fold.css",
            # rental_duration_display.js was removed from the repo but left in the
            # bundle — a missing asset file breaks the whole web.assets_frontend
            # bundle ("Could not get content for ..."), which stops ALL frontend JS
            # (incl. the quote hero/scroll logic) from initializing. Dropped.
            "proquotes/static/src/JS/rental_form_dropdowns.js",
            "proquotes/static/src/CSS/header.css",
            "proquotes/static/src/CSS/store.css",
            "proquotes/static/src/CSS/ccp_selection.css",
            "proquotes/static/src/CSS/image_zoom.css",
            "proquotes/static/src/CSS/address_selector.css",
            "proquotes/static/src/CSS/liquid_glass.css",
            "proquotes/static/src/CSS/quotePreview.css",
            "proquotes/static/src/CSS/invoicePreview.css",
            "proquotes/static/src/JS/price.js",
            "proquotes/static/src/JS/fold.js",
            "proquotes/static/src/JS/rental.js",
            "proquotes/static/src/JS/poNumber.js",
            "proquotes/static/src/JS/rental.js",
            "proquotes/static/src/JS/website_preview.js",
            "proquotes/static/src/JS/ccp_selection.js",
            "proquotes/static/src/JS/image_zoom.js",
            "proquotes/static/src/JS/address_selector.js",
            "proquotes/static/src/JS/liquid_glass.js",
            "proquotes/static/src/JS/quote_hero_overlay.js",
            "proquotes/static/src/JS/quote_communication.js",
            ('replace', 'portal/static/src/signature_form/signature_form.js',
             'proquotes/static/src/JS/signature_form.js'),
        ],
        'web.assets_backend': [
            "proquotes/static/src/CSS/backend.css",
            "proquotes/static/src/JS/website_preview.js",
            "proquotes/static/src/JS/composer_confirmation.js",
            "proquotes/static/src/xml/composer_confirmation.xml",
            "proquotes/static/src/JS/section_translate.js",
            "proquotes/static/src/xml/section_translate.xml",
            "proquotes/static/src/JS/single_choice.js",
            "proquotes/static/src/xml/single_choice.xml",
        ],
        'website.assets_wysiwyg': [
            'proquotes/static/src/JS/rental_quote_form_editor.js',
        ],
    },

    "version": "19.0.1.2.0",

    # always loaded
    "data": [
        "security/ir.model.access.csv",
        # ccp configuration data
        "data/preview_block_data.xml",
        "data/ccp_type_config_data.xml",
        "data/ccp_period_config_data.xml",
        "data/ccp_scanner_config_data.xml",
        # ccp configuration views
        "views/Configuration/ccp_type_config_view.xml",
        "views/Configuration/ccp_period_config_view.xml",
        "views/Configuration/ccp_scanner_config_view.xml",
        # confirmation activity templates
        "views/Configuration/confirmation_activity_view.xml",
        # quotes
        "views/Quote/preview_blocks.xml",
        "views/Quote/quote_report.xml",
        "views/Quote/quote_preview.xml",
        "views/Quote/quote_internal.xml",
        "views/Quote/quote_template.xml",
        "views/Quote/quote_wizard.xml",
        # invoices
        "views/Invoice/invoice_report.xml",
        "views/Invoice/invoice_preview.xml",
        "views/Invoice/invoice_internal.xml",
        # Odoo 19 migration: temporarily disabled. Inherits the Enterprise
        # account_followup.template_followup_report and xpaths into its report
        # table (o_account_reports_table) / internal sub-templates, which changed
        # in v19. Rebuild against the v19 followup report (logo header + drop the
        # Communication column), then re-enable.
        # "views/Invoice/follow_up_email.xml",
        # purchase
        "views/Purchase/purchase_report.xml",
        "views/Purchase/purchase_preview.xml",
        "views/Purchase/purchase_internal.xml",
        # other
        "views/Other/report_footer.xml",
        "views/Other/mail_templates.xml",
        "views/Other/stock_lot.xml",
        # Odoo 19 migration: temporarily disabled. Inherits account.tax_groups_totals
        # (removed in v19) and uses the old amount_by_group data structure (replaced
        # by the tax_totals rendering). This shows French tax labels (TPS/TVH/TVQ) and
        # per-company tax registration numbers on documents — IMPORTANT for CA/QC tax
        # compliance. Rebuild against v19's tax_totals template, then re-enable.
        # "views/Other/tax.xml",
        "views/Other/rentalTerms.xml",
        "views/Other/normalTerms.xml",
        "views/Other/website_logo.xml",
        "views/Other/renewalText.xml",
        "views/Other/rental_order_wizard_form.xml",
        # "views/Quote/quoteRentalAddress.xml",
        "views/Quote/ccp_selection_form.xml",
        # Odoo 19 migration: temporarily disabled. This file wholesale-REDEFINED the
        # core mail.mail_notification_layout with a stale (pre-v19) copy, which clobbers
        # v19's own layout and breaks its child views (e.g. mail_notification_invite's
        # //td[@t-if='subtitles'] xpath). It also removed a row from mail_notification_light.
        # Rebuild the email-layout branding (logo, signature footer, hide "Powered by Odoo")
        # as a proper INHERITED customization of the v19 layout, then re-enable.
        # "views/Other/mail.xml",
        "views/Other/delivery_report.xml",
        "views/Other/project_task.xml",
        "views/Other/section_name.xml",
        "views/Other/res_company.xml",
        "views/Other/res_user.xml",
        "views/Other/renewal.xml",
        "views/Other/header_footer.xml",
        "views/Invoice/invoice_lot.xml",
        "views/Other/stock_picking.xml",
        # Odoo 19 migration: temporarily disabled. Inherits mail.mail_notification_layout
        # but its xpaths match the exact markup of the stale layout copy in Other/mail.xml
        # (e.g. //div[@t-if='subtitles or has_button_access or actions or not is_discussion'])
        # which does not exist in v19's core layout. Rebuild together with the email-layout
        # branding against the v19 layout, then re-enable.
        # "views/Other/quoteEmailFooter.xml",
        "views/Other/helpdeskTicket.xml",
        "views/Other/header_footer_values.xml",
        "views/Other/preconfigured_sections.xml",
        "views/Other/res_config_extend_view.xml",
        "views/Other/picking_sign_wizard_view.xml",
        "views/Other/rental_pricing_mode.xml",
        "views/Other/crm_lead.xml",
        "data/thanks_for_payment.xml",
    ],
}
