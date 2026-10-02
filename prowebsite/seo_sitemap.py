# -*- coding: utf-8 -*-
"""Sitemap location filter. No Odoo imports, so the rules can be unit-tested
and copied onto a later major version without dragging 17-only ORM calls.
"""
import re

# Path prefixes dropped on a segment boundary: "/cont" matches "/cont" and
# "/cont/..." and does not match "/contact-us" or "/contact-information-form".
# "/dev" does not match "/devices".
JUNK_PREFIXES = (
    '/dev',
    '/cont',
    '/telechargement',
    '/website/info',
    '/livechat',
    '/profile',
    '/forum',
    '/slides',
    '/groups',
    '/helpdesk',
    '/calendar',
    '/shop/set_pricelist',
)

# Odoo 17 website_blog registers /blog/<blog>/feed with sitemap=True.
BLOG_FEED_RE = re.compile(r'^/blog/[^/]+/feed$')

# /blog/<blog-slug-id>/<post-slug-id>  (not /blog, not /blog/<blog>, not /feed)
BLOG_POST_RE = re.compile(r'^/blog/([^/]+)/([^/]+)$')

# Same trailing-id rule as Odoo 17 http_routing.models.ir_http._UNSLUG_RE,
# anchored to the whole slug (the route regex also allows a query or hash).
UNSLUG_RE = re.compile(
    r'(?:(\w{1,2}|\w[A-Za-z0-9-_]+?\w)-)?(-?\d+)$'
)


def normalize_loc(loc):
    """Return the path of a sitemap loc, without query, fragment or trailing slash."""
    if not loc:
        return ''
    path = loc.strip()
    if '://' in path:
        path = path.split('://', 1)[1]
        path = '/' + path.split('/', 1)[1] if '/' in path else '/'
    path = path.split('?', 1)[0].split('#', 1)[0]
    if len(path) > 1:
        path = path.rstrip('/')
    if not path.startswith('/'):
        path = '/' + path
    return path or '/'


def has_segment_prefix(path, prefix):
    return path == prefix or path.startswith(prefix + '/')


def unslug_id(slug):
    """Return the integer id at the end of an Odoo slug, or None."""
    if not slug:
        return None
    match = UNSLUG_RE.match(slug)
    if not match:
        return None
    return int(match.group(2))


def skip_loc(loc, post_blog_id_of):
    """Return True when this sitemap loc should be omitted.

    ``post_blog_id_of(post_id)`` returns the post's ``blog_id`` id, or None
    when the post cannot be resolved. Unresolved posts are kept: a lookup
    miss must not hide the one canonical URL.
    """
    path = normalize_loc(loc)
    if any(has_segment_prefix(path, prefix) for prefix in JUNK_PREFIXES):
        return True
    if BLOG_FEED_RE.match(path):
        return True
    post_match = BLOG_POST_RE.match(path)
    if not post_match:
        return False
    blog_id = unslug_id(post_match.group(1))
    post_id = unslug_id(post_match.group(2))
    # Blog index pagination and tag paths that happen to have two segments
    # but no Odoo id stay in the sitemap.
    if blog_id is None or post_id is None:
        return False
    owner_blog_id = post_blog_id_of(post_id)
    if owner_blog_id is None:
        return False
    return owner_blog_id != blog_id


def rendered_robots_user_agent_count(robots_txt, allowed_routes=()):
    """Count ``User-agent:`` lines the way Odoo 17 renders /robots.txt.

    The website.robots template prints one ``User-agent: *`` group, then the
    ``Sitemap:`` line, then ``website.robots_txt``. The controller appends a
    second group only when ``_get_allowed_robots_routes()`` is non-empty.
    The base implementation of that hook returns an empty list.
    """
    parts = [
        'User-agent: *',
        'Sitemap: https://www.example.com/sitemap.xml',
        '',
        '',
        '##############',
        '#   custom   #',
        '##############',
        '',
        robots_txt or '',
    ]
    content = '\n'.join(parts)
    if allowed_routes:
        content += '\nUser-agent: *'
        content += '\n' + '\n'.join('Allow: %s' % route for route in allowed_routes)
    return content.count('User-agent:')
