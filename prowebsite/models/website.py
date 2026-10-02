# -*- coding: utf-8 -*-
"""Drop junk and duplicate blog-post URLs from the sitemap.

Odoo 17 ``Website._enumerate_pages(self, query_string=None, force=False)``
yields one dict per loc. Blog posts are not yielded by a custom sitemap
callable. ``website_blog`` registers this route with ``sitemap=True``:

    /blog/<model("blog.blog"):blog>/<model("blog.post",
        "[('blog_id','=',blog.id)]"):blog_post>

``_enumerate_pages`` expands that route through ``ModelConverter.generate``,
which ``safe_eval``s the converter domain. The domain is supposed to keep
each post under its own blog. Two things stop that from happening here:

1. ``to_python`` never applies the domain. It only reads the id out of the
   slug. The controller then 301s when ``blog_post.blog_id`` is not the blog
   in the URL, which is why the non-canonical locs are redirects.
2. ``ewall_seo_urls`` replaces the converter and its ``__init__`` calls
   ``super(ModelConverter, self).__init__(url_map, model)`` without the
   ``domain`` argument. Every converter therefore keeps the default
   domain ``[]``. ``_enumerate_pages`` then rewrites an empty domain on a
   model that has ``website_id`` to a website filter only. ``blog.post`` has
   ``website_id``, so each post is combined with every blog.

This override does not trust that domain. It parses
``/blog/<blog-slug-id>/<post-slug-id>`` with the Odoo 17 unslug rule and
keeps the loc only when the blog id is ``post.blog_id``. ``/blog`` and
``/blog/<blog>`` are not post URLs and stay. Locale prefixes are not added;
enumeration already runs in the website's default language.

On Odoo 19, ``slug`` / ``unslug`` moved to ``ir.http._slug`` and the blog
controller builds domains with ``Domain`` objects. This filter only looks
at the loc string and ``blog.post.blog_id``, so it does not call those APIs.
"""
import logging

from odoo import models

from odoo.addons.prowebsite.seo_sitemap import skip_loc

_logger = logging.getLogger(__name__)


class Website(models.Model):
    _inherit = 'website'

    def _seo_post_blog_id(self, post_id):
        """Return ``blog.post.blog_id`` for ``post_id``, or None if unknown."""
        if 'blog.post' not in self.env:
            return None
        post = self.env['blog.post'].sudo().browse(post_id).exists()
        if not post:
            return None
        return post.blog_id.id or None

    def _seo_batch1_skip_loc(self, loc, post_blog_ids=None):
        cache = post_blog_ids if post_blog_ids is not None else {}

        def post_blog_id_of(post_id):
            if post_id not in cache:
                cache[post_id] = self._seo_post_blog_id(post_id)
            return cache[post_id]

        return skip_loc(loc, post_blog_id_of)

    def _enumerate_pages(self, query_string=None, force=False):
        # Odoo 17 signature. Do not add a lang argument: that would emit
        # /fr_CA and /es locs, which this batch does not put in the sitemap.
        post_blog_ids = {}
        for page in super()._enumerate_pages(query_string=query_string, force=force):
            loc = page.get('loc') if isinstance(page, dict) else None
            if self._seo_batch1_skip_loc(loc, post_blog_ids):
                continue
            yield page
