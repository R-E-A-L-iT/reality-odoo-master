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
        # Rebuilt for Odoo 19 (anchors taken from this DB's combined arch).
        # Add-to-cart gating now inherits website_sale.cta_wrapper, which is where
        # v19 moved #add_to_cart_wrap; the financing section anchors after the
        # cta_wrapper call. See the file header for what was dropped and why.
        "views/website_sale_product.xml",
        "views/product_template_form.xml",
        # Odoo 19 migration: temporarily disabled to show the default store.
        # "views/wishlist_page.xml",
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
        # Odoo 19 migration: temporarily disabled to show the default store cart.
        # "views/website_cart.xml",
    ],
}