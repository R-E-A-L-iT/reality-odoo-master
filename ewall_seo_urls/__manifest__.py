# -*- coding: utf-8 -*-
{
    "name": """Ecommerce SEO URLs""",
    "summary": """You have the flexibility to personalize product and shop page URLs, 
                making them independent of the product's name or ID. 
                Basically you can have either the product name or Product ID on the URLs for SEO purposes""",
    "description": """Customize your product and shop page URLs effortlessly, 
                        decoupling them from specific product names or IDs. 
                        Enjoy the flexibility to craft distinct web addresses that resonate with your brand. 
                        This feature not only enhances your website's structure but also boosts SEO and improves the overall user experience. 
                        Take charge of your online presence with personalized product page URLs, making navigation smoother for your customers.""",
    "category": "eCommerce",
    "version": "17.0",
    "author": "EWall Solutions Pvt. Ltd.",
    "support": "support@ewallsolutions.com",
    "website": "http://www.ewallsolutions.com",
    'maintainer': 'EWall Solutions Pvt. Ltd.',
    'company': "EWall Solutions Pvt. Ltd. ",
    'currency':'USD',
    'license': 'OPL-1',
    'price':'57.00',
    "depends": ["base", "product","website_sale"],
    "external_dependencies": {"python": [], "bin": []},
    "data": ["views/product_seo_url.xml","views/product_category_seo_url_template.xml"],
    'assets': {
        'web.assets_frontend': [
            'ewall_seo_urls/static/src/js/product_attribute.js',
        ],
    },
    'images': [
        'static/description/images/banner.png',
    ],
    "post_load": "post_load",
    "pre_init_hook": None,
    "post_init_hook": None,
    "installable": True,
    "auto_install": False,
}
