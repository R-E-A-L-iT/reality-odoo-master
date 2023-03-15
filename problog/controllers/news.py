# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import http, fields
from odoo.addons.http_routing.models.ir_http import slug, unslug
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.portal.controllers.portal import _build_url_w_params
from odoo.http import request
from odoo.osv import expression
from odoo.tools import html2plaintext
from odoo.tools.misc import get_lang
from odoo.tools import sql

from odoo.addons.website_blog.controllers.main import WebsiteBlog as Blog


import logging
_logger = logging.getLogger(__name__)


class WebsiteNews(Blog):
    @http.route([
        '/news',
        '/news/page/<int:page>',
        '/news/tag/<string:tag>',
        '/news/tag/<string:tag>/page/<int:page>',
        '''/news/<model("blog.blog"):blog>''',
        '''/news/<model("blog.blog"):blog>/page/<int:page>''',
        '''/news/<model("blog.blog"):blog>/tag/<string:tag>''',
        '''/news/<model("blog.blog"):blog>/tag/<string:tag>/page/<int:page>''',
    ], type='http', auth="public", website=True, sitemap=True)
    def news(self, blog=None, tag=None, page=1, search=None, **opt):
        return self.blog(blog=blog, tag=tag, page=page, serach=search, opt=opt)

    @http.route([
        '''/news/<model("blog.blog"):blog>/<model("blog.post"):blog_post>''',
    ], type='http', auth="public", website=True, sitemap=True)
    def news_post(self, blog, blog_post, tag_id=None, page=1, enable_editor=None, **post):
        blog_record = request.env['blog.blog'].search(
            [('name', '=', 'NEWS')])
        return self.blog_post(blog=blog_record, blog_post=blog_post, tag_id=tag_id,
                              enable_editor=enable_editor, post=post)
