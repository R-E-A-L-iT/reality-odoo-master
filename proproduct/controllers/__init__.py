# Odoo 19 migration: temporarily disabled so the store renders with the default
# Odoo 19 website_sale controllers. These override /shop, /shop/set_pricelist,
# product values and the sitemap; several call website_sale internals whose
# signatures changed in v19 (e.g. _shop_get_query_url_kwargs). Re-enable/port
# individually once the default store is validated.
# from . import website_sale
# from . import table_compute
