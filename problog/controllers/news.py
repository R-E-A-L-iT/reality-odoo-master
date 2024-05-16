# -*- coding: utf-8 -*-

from collections import OrderedDict

from odoo import http
from odoo.http import request

from odoo.addons.website_blog.controllers.main import WebsiteBlog as Blog


import logging

_logger = logging.getLogger(__name__)


class WebsiteNews(Blog):
    # Setup /news url for the blog
    @http.route(
        [
            "/news",
            "/news/page/<int:page>",
            "/news/tag/<string:tag>",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def news(self, blog=None, tag=None, page=1, search=None, **opt):
        print('>>>>>>>>>>>>>>>>> news ????????????????????/')
        return self.blog(blog=blog, tag=tag, page=page, serach=search, opt=opt)

    @http.route(
        [
            """/news/<model("blog.post"):blog_post>""",
        ],
        type="http",
        auth="public",
        website=True,
        sitemap=True,
    )
    def news_post(self, blog_post, tag_id=None, page=1, enable_editor=None, **post):
        print('>>>>>>>>>>>>>>>>> news_post ????????????????????/')
        blog_record = request.env["blog.blog"].search([("name", "=", "NEWS")])
        return self.blog_post(
            blog=blog_record,
            blog_post=blog_post,
            tag_id=tag_id,
            enable_editor=enable_editor,
            post=post,
        )
