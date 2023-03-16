
{
    'name': "ProBlog",

    'summary': """
        Styles and Structures Related to Blog
    """,

    'description': """
        Module That Improves the Style and Design of the Blog
	""",

    'author': "Ty Cyr",

    'license': "LGPL-3",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Website',
    # Blog post content
    'version': '0.191',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website', 'website_blog'],
    'assets': {
            'web.assets_frontend': [
                'problog/static/css/blog.css',
            ]
    },

    # always loaded
    'data': [
        'views/blog_menu.xml',
        'views/blog_page.xml',
        'views/blog_backend.xml',
        'views/blog_date.xml',
        'views/blog_posts.xml',
        'views/blog_post_heading.xml',
        'views/blog_post_cover_image.xml',
        'views/blog_info.xml',
        'views/blog_post_content.xml',
        'views/blog_teaser.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
