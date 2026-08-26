# -*- coding: utf-8 -*-
{
    "name": "ProWebsite",
    "summary": """
        Helper module to add website features""",
    "description": """
        Helper module to add website features
    """,
    "author": "Ézékiel deBlois",
    "license": "LGPL-3",
    "category": "Technical",
    "version": "19.0.1.0.0",
    'application': True,
    "depends": [
        "base",
        "website_sale",
        "crm",
    ],
    'assets': {
        'web.assets_frontend': [
            # ── Stylesheets ──────────────────────────────────────────────────
            # The Odoo 17 store stylesheets (product_page.css / shop_page.css)
            # were DELETED, not disabled: their selectors were written against
            # the Odoo 17 website_sale markup and no longer matched in 19, and
            # the store now stays on Odoo's default look by design. Nothing here
            # targets the stock shop/product/cart/checkout pages any more.
            'prowebsite/static/src/css/header_dropdowns.css',
            # Broad custom stylesheet: site header, hero/landing sections, FAQ,
            # promos, review cards, video gallery, "notify me" signup.
            'prowebsite/static/src/css/three_product.css',
            'prowebsite/static/src/css/rtc_series.css',
            'prowebsite/static/src/css/rtc_series_sections.css',
            # Reusable product-marketing content sections (.o_rtc_page +
            # .o_rtc_feature_row / _media_card / _reviews / _cta ...). These are
            # the building blocks the REDESIGNED product pages are authored
            # against (BLK2GO etc.), layered on top of rtc_series_sections.css.
            # Nothing here touches the stock website_sale markup.
            'prowebsite/static/src/css/product_sections.css',
            'prowebsite/static/src/css/rtc_demo_request.css',
            # Reusable product demo / lead request form (.o_rtc_lead_form) — the
            # paste-able "See it in action" block on the redesigned product pages.
            'prowebsite/static/src/css/product_lead.css',
            # Leica MultiMapper landing page — scoped entirely under .o_mm_page.
            'prowebsite/static/src/css/multimapper.css',

            # ── Scripts ──────────────────────────────────────────────────────
            # Every script is feature-detected: each one bails out early when the
            # page doesn't contain its markup, so they're no-ops elsewhere.
            'prowebsite/static/src/js/header_dropdowns.js',
            'prowebsite/static/src/js/rtc_series.js',
            'prowebsite/static/src/js/rtc_scroll_model.js',
            'prowebsite/static/src/js/rtc_demo_request.js',
            # Posts to /product_demo/submit (see controllers/main.py) — creates a
            # CRM lead titled by the product the visitor is enquiring about.
            'prowebsite/static/src/js/product_lead.js',
            # Posts to /tradeshow_signup/submit — tradeshow / "stay in the loop"
            # contact signup, feeds the same Sales pipeline as the demo requests.
            'prowebsite/static/src/js/tradeshow_signup.js',
            'prowebsite/static/src/js/multimapper.js',
            # Site-wide features, extracted out of three_product.js so they no
            # longer depend on it loading or succeeding. Do NOT re-add these
            # calls to three_product.js — they would double-initialise (the
            # video gallery would clone its slides twice).
            'prowebsite/static/src/js/video_gallery.js',
            'prowebsite/static/src/js/faq_accordion.js',
            'prowebsite/static/src/js/notify_signup.js',
            'prowebsite/static/src/js/review_cards.js',
            'prowebsite/static/src/js/promo_popups.js',
            # Store-page scripts (kept — only the store CSS was dropped):
            #   product_page.js  → appends the currency code after the price
            #   three_product.js → 3D product viewer + add-to-cart buy section,
            #                      OmniGO page header/cursor/loading screen
            'prowebsite/static/src/js/product_page.js',
            'prowebsite/static/src/js/three_product.js',
        ],
    }
}