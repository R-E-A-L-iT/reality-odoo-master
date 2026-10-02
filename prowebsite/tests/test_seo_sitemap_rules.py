# -*- coding: utf-8 -*-
"""Rules for the sitemap filter and the robots block.

These tests do not need a database. The Odoo test runner can still collect
them; ``python -m unittest`` can run this file on its own.
"""
import importlib.util
import unittest
from pathlib import Path


def _load(name):
    try:
        module = __import__('odoo.addons.prowebsite.' + name, fromlist=[name])
        return module
    except ImportError:
        path = Path(__file__).resolve().parents[1] / (name + '.py')
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


seo_sitemap = _load('seo_sitemap')
seo_batch1_data = _load('seo_batch1_data')


class TestSitemapFilter(unittest.TestCase):
    def setUp(self):
        # post 51 lives on blog 2 (news). The other blogs are the duplicates.
        self.owner = {51: 2, 48: 8, 52: 11}

    def _skip(self, loc):
        return seo_sitemap.skip_loc(loc, lambda post_id: self.owner.get(post_id))

    def test_junk_prefixes_drop_on_a_segment_boundary(self):
        dropped = [
            '/dev',
            '/dev/foo',
            '/cont',
            '/cont/forward',
            '/telechargement',
            '/website/info',
            '/livechat',
            '/livechat/channel/www-r-e-a-l-it-2',
            '/livechat/channel/www-r-e-a-l-it-fr-3',
            '/profile/users',
            '/profile/ranks_badges',
            '/forum',
            '/slides',
            '/slides/all',
            '/groups',
            '/helpdesk',
            '/calendar',
            '/shop/set_pricelist',
        ]
        for loc in dropped:
            self.assertTrue(self._skip(loc), loc)

    def test_nearby_pages_and_money_pages_stay(self):
        kept = [
            '/contact-us',
            '/contact-information-form',
            '/devices',
            '/appointment',
            '/rental/scanners',
            '/rental/scanners/blkarc',
            '/rental/scanners/blk2fly',
            '/capture/software/cloudworx',
            '/capture/software/cyclone-enterprise',
            '/shop/rtc700-surveyor-package-593850',
            # The old product slug is not a filter rule. A fresh enumeration
            # stops emitting it once the product slug is the current one.
            '/shop/6020223-rtc700-surveyor-package-593850',
            '/blog',
            '/blog/news-2',
            '/blog/case-studies-11',
        ]
        for loc in kept:
            self.assertFalse(self._skip(loc), loc)

    def test_blog_feeds_are_dropped(self):
        for loc in (
            '/blog/hardware-8/feed',
            '/blog/solutions-10/feed',
            '/blog/case-studies-11/feed',
            '/blog/software-9/feed',
            '/blog/news-2/feed',
        ):
            self.assertTrue(self._skip(loc), loc)

    def test_duplicate_blog_posts_are_dropped_and_the_canonical_url_stays(self):
        # post 51 belongs to blog 2, post 48 to blog 8, post 52 to blog 11.
        # A digit inside the slug (rtc360) must not be read as the record id.
        self.assertTrue(self._skip(
            '/blog/case-studies-11/new-toronto-office-51'
        ))
        self.assertTrue(self._skip(
            '/blog/case-studies-11/leica-rtc360-features-capabilities-specs-48'
        ))
        self.assertTrue(self._skip(
            '/blog/news-2/bermuda-unfinished-church-52'
        ))
        self.assertFalse(self._skip(
            '/blog/news-2/new-toronto-office-51'
        ))
        self.assertFalse(self._skip(
            '/blog/hardware-8/leica-rtc360-features-capabilities-specs-48'
        ))
        self.assertFalse(self._skip(
            '/blog/case-studies-11/bermuda-unfinished-church-52'
        ))

    def test_unresolved_post_is_kept(self):
        self.assertFalse(self._skip('/blog/news-2/missing-post-999'))

    def test_slug_without_an_id_is_kept(self):
        # A custom seo_url with no trailing id is not a duplicate we can prove.
        self.assertFalse(self._skip('/blog/news/some-post'))

    def test_trailing_slash_and_query_do_not_bypass_the_filter(self):
        self.assertTrue(self._skip('/dev/'))
        self.assertTrue(self._skip('/blog/news-2/feed/'))
        self.assertFalse(self._skip('/contact-us/'))
        self.assertFalse(self._skip('/rental/scanners?utm_source=google-g'))

    def test_unslug_ids_match_the_live_blog_slugs(self):
        samples = {
            'news-2': 2,
            'hardware-8': 8,
            'software-9': 9,
            'solutions-10': 10,
            'case-studies-11': 11,
            'new-toronto-office-51': 51,
            '2021-pointfuse-v9-update-9': 9,
            'c10-7': 7,
            'blk2fly-35': 35,
            'unveiling-the-distinctions-leica-rtc360-vs-leica-p-series-laser-scanners-49': 49,
            'leica-rtc360-features-capabilities-specs-48': 48,
        }
        for slug, expected in samples.items():
            self.assertEqual(seo_sitemap.unslug_id(slug), expected, slug)
        self.assertIsNone(seo_sitemap.unslug_id('feed'))
        self.assertIsNone(seo_sitemap.unslug_id('contact-us'))


class TestRobotsBlock(unittest.TestCase):
    def test_custom_block_is_the_disallow_list_and_one_allow(self):
        text = seo_batch1_data.ROBOTS_TXT
        self.assertNotIn('User-agent', text)
        self.assertNotIn('user-agent', text.lower())
        self.assertNotRegex(text.lower(), r'allow\s+\*')
        self.assertNotIn('allow *', text.lower())
        self.assertIn('Disallow: /website/info\n', text)
        self.assertIn('Disallow: /shop/set_pricelist\n', text)
        self.assertIn('Disallow: /shop/cart\n', text)
        self.assertIn('Disallow: /shop/checkout\n', text)
        self.assertIn('Disallow: /web/login\n', text)
        self.assertIn('Disallow: /web/signup\n', text)
        self.assertIn('Disallow: /web/reset_password\n', text)
        self.assertIn('Disallow: /my/\n', text)
        self.assertIn('Allow: /social_instagram/\n', text)
        # Money pages and query strings are not disallowed.
        self.assertNotIn('/rental', text)
        self.assertNotIn('utm', text.lower())
        self.assertNotIn('Disallow: /web/\n', text)
        self.assertNotIn('Disallow: /web\n', text)

    def test_rendered_template_has_one_user_agent_group(self):
        text = seo_batch1_data.ROBOTS_TXT
        self.assertEqual(seo_sitemap.rendered_robots_user_agent_count(text), 1)
        # The 17 controller adds a second group only when the hook returns routes.
        self.assertEqual(
            seo_sitemap.rendered_robots_user_agent_count(text, allowed_routes=['/social_instagram/']),
            2,
        )

    def test_hub_title_is_the_main_title(self):
        title, description = seo_batch1_data.PAGE_META['/rental/scanners']['en_US']
        self.assertEqual(
            title,
            'Leica Scanner Rentals: RTC360, BLK360, BLK2GO & BLK ARC',
        )
        self.assertNotIn('| REALiT', title)
        self.assertNotIn('Tripod', title)
        self.assertNotIn('ARK', title)
        self.assertNotIn('ARK', description)
        arc_title, arc_description = seo_batch1_data.PAGE_META['/rental/scanners/blkarc']['en_US']
        self.assertIn('BLK ARC', arc_title)
        self.assertNotIn('ARK', arc_title)
        self.assertNotIn('ARK', arc_description)


class TestArchTermMapping(unittest.TestCase):
    def test_substring_replacement_is_idempotent(self):
        old = seo_batch1_data.YEAR_OLD
        new = seo_batch1_data.YEAR_NEW
        term = (
            'REALiT Solutions is a trusted and authorized reseller of '
            'Leica Geosystems equipment since 2022. As a Diamond Partner, we continue.'
        )
        self.assertIn(old, term)
        replaced = term.replace(old, new)
        self.assertIn(new, replaced)
        self.assertNotIn(old, replaced)
        # A second pass finds nothing to change.
        self.assertEqual(replaced.replace(old, new), replaced)
        self.assertNotIn('2022', replaced)

    def test_ark_replacement_does_not_touch_blk_arc(self):
        text = 'Leica BLK ARC and a leftover BLK ARK typo'
        replaced = text.replace(seo_batch1_data.ARK_OLD, seo_batch1_data.ARK_NEW)
        self.assertEqual(replaced, 'Leica BLK ARC and a leftover BLK ARC typo')
        self.assertEqual(replaced.replace(seo_batch1_data.ARK_OLD, seo_batch1_data.ARK_NEW), replaced)
