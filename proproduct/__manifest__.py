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
    "version": "17.0",
    "depends": [
        "base",
        "website",
        "product",
        "website_sale",
        "payment",
        "maintenance",
    ],
    "data": [
        "views/website_sale_product.xml",
        "views/product_template_form.xml",
        "views/wishlist_page.xml",
        "views/website_address.xml",
        "views/maintenance_equipment_views.xml",
    ],
}