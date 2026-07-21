# -*- coding: utf-8 -*-
#
# NEUTRALIZED FOR THE ODOO 19 MIGRATION
# -------------------------------------
# The original version of this file monkey-patched http_routing's module-level
# slug/slugify_one helpers and installed a custom URL ModelConverter so that
# incoming request URLs containing a custom SEO slug resolved back to the right
# product/category record.
#
# Odoo 19 removed those module-level helpers (slug / unslug / slugify /
# slugify_one / _UNSLUG_RE) in favour of ir.http model methods
# (_slug / _unslug / _slugify) and reworked the URL converters, so the original
# code cannot import or run. Re-implementing the custom converter against the new
# converter API is deferred; this file is intentionally left as an import-safe
# no-op so the database can boot.
#
# What still works after neutralization:
#   * SEO slug *generation* (seo_url.py and product_category_seo_url.py port the
#     slug() / slugify() calls to env['ir.http']._slug() / _slugify()).
#   * The website_sale controller overrides that resolve a category by its
#     seo_url via an explicit search().
# What is degraded until the converter is ported:
#   * Custom-slug *resolution* for product-template URLs falls back to Odoo's
#     standard /shop/<model(...)> behaviour.
