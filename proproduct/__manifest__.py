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
        "views/website_sale_product.xml",
        "views/product_template_form.xml",
        "views/wishlist_page.xml",
        "views/website_address.xml",
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