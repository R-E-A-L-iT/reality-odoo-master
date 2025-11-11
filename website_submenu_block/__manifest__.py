{
    'name': 'Website Submenu Block',
    'version': '17.0.1.8.0',
    'category': 'Website/Website',
    'summary': 'Sticky submenu navigation block for websites',
    'description': """
Website Submenu Block
=====================

This module adds a customizable submenu block that can be used as a secondary navigation 
on website pages. The submenu block features:

* Sticky positioning below the main header
* Customizable colors and spacing through website editor
* Responsive design (hidden on mobile devices)
* Anchor navigation to page sections
* Optional usage per page

Perfect for creating table of contents, section navigation, or quick access menus.
    """,
    'author': 'Braincrew Apps',
    'website': 'http://www.braincrewapps.com',
    'depends': [
        'website',
        'web_editor',
    ],
    'data': [
        'views/snippets/s_submenu_block.xml',
        'views/snippets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'website_submenu_block/static/src/snippets/s_submenu_block/000.scss',
            'website_submenu_block/static/src/snippets/s_submenu_block/000.js',
        ],
        'web_editor.assets_wysiwyg': [
            'website_submenu_block/static/src/snippets/s_submenu_block/options.js',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}