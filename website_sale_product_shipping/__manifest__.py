{
    'name': 'Per-Product Shipping Methods',
    'version': '17.0.1.0.0',
    'summary': 'Control which shipping methods appear per product at e-commerce checkout',
    'category': 'Website/eCommerce',
    'author': 'Braincrew Apps',
    'depends': ['website_sale', 'delivery', 'sale'],
    'data': [
        'views/product_template_views.xml',
        'views/delivery_carrier_views.xml',
        'views/website_sale_delivery_templates.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_sale_product_shipping/static/src/js/website_sale_per_product_delivery.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
