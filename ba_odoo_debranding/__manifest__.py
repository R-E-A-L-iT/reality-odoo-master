# -*- coding: utf-8 -*-
{
    'name': 'Odoo Debranding',
    'version': '1.0',
    'author': 'Braincrew Apps',
    'category': 'Productivity',
    'website': 'http://www.braincrewapps.com',
    'license': 'LGPL-3',
    'sequence': 999,
    'summary': """
        Odoo Debranding
    """,
    'description': """
        Odoo Debranding
    """,
    'images': [],
    'depends': [
        'base_setup',
        'web',
        'mail',
        'iap',
        'auth_signup',
        'portal'
    ],
    'data': [
        'security/res_groups.xml',
        'security/ir.model.access.csv',
        'views/app_theme_config_settings_views.xml',
        #'views/res_config_settings_views.xml',
        'views/ir_views.xml',
        'views/branding_templates.xml',
        # data
        'data/ir_config_parameter_data.xml',
        # 'data/digest_template_data.xml',
    ],
    'qweb': [
        'static/src/xml/*.xml',
    ],
    'assets': {
        'web.assets_backend': [
            '/ba_odoo_debranding/static/src/scss/app.scss',
            '/ba_odoo_debranding/static/src/scss/dialog.scss',
            '/ba_odoo_debranding/static/src/js/app_window_title.js',
            '/ba_odoo_debranding/static/src/js/dialog.js',
        ],
    },
    'demo': [],
    'test': [],
    'css': [],
    'js': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}
