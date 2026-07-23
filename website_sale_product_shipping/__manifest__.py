{
    'name': 'Per-Product Shipping Methods',
    'version': '19.0.1.0.0',
    'summary': 'Control which shipping methods appear per product at e-commerce checkout',
    'category': 'Website/eCommerce',
    'author': 'Braincrew Apps',
    'depends': ['website_sale', 'delivery', 'sale'],
    'data': [
        'views/product_template_views.xml',
        'views/delivery_carrier_views.xml',
        # Odoo 19 migration: temporarily disabled. These inherit website_sale
        # checkout templates (payment_delivery / cart_delivery) and xpath into
        # //div[@id='delivery_carrier'] / //tr[@id='order_delivery'], markup that
        # v19 reworked. Rebuild the per-product checkout delivery UI against v19,
        # then re-enable. (Backend fields/views + model logic stay active.)
        # 'views/website_sale_delivery_templates.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            # Odoo 19 migration: temporarily disabled (per-product checkout delivery
            # UI is neutralized until rebuilt for the v19 checkout).
            # 'website_sale_product_shipping/static/src/js/website_sale_per_product_delivery.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': False,
    'license': 'LGPL-3',
}
