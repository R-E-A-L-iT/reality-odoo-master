{
    "name": "ProProduct",
    "summary": """
		Product upgrade module that adds approve financing availability and other Ecommerce features.""",
    "description": """
		Product upgrade module that adds approve financing availability and other Ecommerce features.
	""",
    "author": "Ezekiel deBlois",
    "license": "LGPL-3",
    "category": "Sales",
    "version": "19.0.1.0.0",
    "depends": [
        "base",
        "website",
        "product",
        "website_sale",
        "website_sale_renting",
        "payment",
        "maintenance",
    ],
    "data": [
        # Odoo 19 migration: temporarily disabled. This view inherits
        # website_sale.product and xpaths into markup that changed in v19 — the
        # //t[@t-cache] wrapper was removed (the pricelist-forcing/price-lock
        # blocks worked around a v17 t-cache stale-currency bug that no longer
        # exists), and //div[@id='o_product_terms_and_share'] was removed. Rebuild
        # it against the v19 product template — keeping the add-to-cart region
        # gating and the financing section — then re-enable.
        # "views/website_sale_product.xml",
        "views/product_template_form.xml",
        "views/wishlist_page.xml",
        # Odoo 19 migration: temporarily disabled. Restricts the checkout country
        # dropdown by xpath-replacing //select[@id='country_id']/t[@t-foreach='countries'],
        # but v19 rewrote the checkout address form and that static markup is gone.
        # Reimplement the currency-based country restriction at the controller
        # level (filter the `countries` passed to the address form), then re-enable.
        # "views/website_address.xml",
        "views/maintenance_equipment_views.xml",
        # Odoo 19 migration: temporarily disabled. This view inherits the
        # Enterprise website_sale_renting.rental_product template and its xpaths
        # (//div[hasclass('js_main_product')]//t[@t-placeholder='select']/... and
        # //div[@id='product_documents']/preceding-sibling::t[1]) target pre-v19
        # markup that changed. Re-anchor against the actual v19 rental_product
        # arch, then re-enable. See views/website_sale_product_renting.xml.
        # "views/website_sale_product_renting.xml",
        "views/website_cart.xml",
    ],
}