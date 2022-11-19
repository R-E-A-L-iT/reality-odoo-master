# -*- coding: utf-8 -*-
{
    'name': "Proquotes",

    'summary': """
		Quote Upgrade Module that adds Advanced Features""",

    'description': """
		Module that allows advanced Quote features. Like Folding Sections, Improved Optional Products, and Multiple Choice Sections
	""",

    'author': "Ty Cyr",

    'license': "LGPL-3",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Sales',


    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'mail', 'account', 'proportal', 'product', 'website', 'sale_management', 'sale', 'digest', 'portal'],

    'assets': {
            'web.assets_frontend': [
                'proquotes/static/src/CSS/foldProducts.css',
                'proquotes/static/src/CSS/pdf.css',
                'proquotes/static/src/CSS/user-info.css',
                'proquotes/static/src/CSS/login.css',
                'proquotes/static/src/CSS/quoteStyle.css',
                'proquotes/static/src/CSS/quoteHeaderText.css',
                'proquotes/static/src/JS/fold.js',
                'proquotes/static/src/JS/poNumber.js',
                'proquotes/static/src/JS/price.js',
                'proquotes/static/src/JS/rental.js',
            ]
    },

    'version': '0.4',

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/quotesFrontend.xml',
        'views/quotesPDF.xml',
        'views/invoicePDF.xml',
        'views/quotesBackend.xml',
        'views/tax.xml',
        'views/mail.xml',
        'views/quotesTemplates.xml',
        'views/quoteLogo.xml',
        'views/renewalText.xml',
        'views/rentalTerms.xml',
        'views/invoiceBackend.xml',
        'views/deliverPDF.xml',
        #         'models/quoteNotify.py'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
