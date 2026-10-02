# -*- coding: utf-8 -*-
"""Database tests for the migration helpers and the sitemap override.

They need an Odoo database with website installed (website 1 is the default
website in the standard test database). They are not run in the agent
environment.
"""
import base64

from odoo.tests import TransactionCase, tagged

from odoo.addons.prowebsite.seo_batch1_data import (
    ARK_NEW,
    ARK_OLD,
    PAGE_META,
    ROBOTS_TXT,
    YEAR_NEW,
    YEAR_OLD,
)
from odoo.addons.prowebsite.seo_migrate import (
    active_spanish_code,
    apply_page_meta,
    clear_sitemap_attachments,
    migrate_seo_batch1,
    replace_arch_substring,
)


# t-name stops the wrapper from being one translation term, so the year
# sentence and the ARK sentence are separate terms (same as a QWeb page).
ARCH = """
<div t-name="prowebsite.seo_batch1_arch">
    <p class="lead">authorized reseller of Leica Geosystems equipment since 2022. As a Diamond Partner</p>
    <p>Leica BLK ARK laser scanner</p>
</div>
"""


@tagged('post_install', '-at_install')
class TestSeoBatch1Migration(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].browse(1)
        if cls.website.exists():
            cls.env['res.lang']._activate_lang('fr_CA')
            cls.env['res.lang']._activate_lang('es_ES')

    def setUp(self):
        super().setUp()
        if not self.website.exists():
            self.skipTest('website id 1 is not present')

    def _terms_rewritten(self, section):
        total = 0
        for per_view in section.values():
            for info in per_view.values():
                total += info.get('terms') or 0
        return total

    def _view_and_page(self, url, arch, key):
        view = self.env['ir.ui.view'].create({
            'name': 'SEO batch1 %s' % url,
            'type': 'qweb',
            'arch': arch,
            'key': key,
            'website_id': self.website.id,
        })
        page = self.env['website.page'].create({
            'view_id': view.id,
            'url': url,
            'website_id': self.website.id,
            'is_published': True,
        })
        return view, page

    def test_meta_write_is_idempotent_and_uses_es_es(self):
        _view, page = self._view_and_page(
            '/rental/scanners-seo-batch1-test',
            '<div>rentals</div>',
            'prowebsite.seo_batch1_meta_test',
        )
        self.assertEqual(active_spanish_code(self.env), 'es_ES')
        meta = PAGE_META['/rental/scanners']
        first = apply_page_meta(self.env, page, meta, 'es_ES')
        second = apply_page_meta(self.env, page, meta, 'es_ES')
        self.assertEqual(first['applied'], second['applied'])
        self.assertEqual(
            page.with_context(lang='en_US').website_meta_title,
            meta['en_US'][0],
        )
        self.assertEqual(
            page.with_context(lang='fr_CA').website_meta_description,
            meta['fr_CA'][1],
        )
        self.assertEqual(
            page.with_context(lang='es_ES').website_meta_title,
            meta['es'][0],
        )
        self.assertNotIn('Tripod', page.with_context(lang='en_US').website_meta_title)
        self.assertNotIn('ARK', page.with_context(lang='en_US').website_meta_description)

    def test_stale_og_image_is_cleared_once(self):
        _view, page = self._view_and_page(
            '/rental/scanners-seo-batch1-og',
            '<div>rentals</div>',
            'prowebsite.seo_batch1_og_test',
        )
        page.website_meta_og_img = '/web/image/tripods-banner.jpg'
        apply_page_meta(self.env, page, PAGE_META['/rental/scanners'], 'es_ES')
        self.assertFalse(page.website_meta_og_img)
        again = apply_page_meta(self.env, page, PAGE_META['/rental/scanners'], 'es_ES')
        self.assertFalse(again['og_img_cleared'])

    def test_arch_replacements_keep_other_languages_and_are_idempotent(self):
        view, _page = self._view_and_page(
            '/seo-batch1-arch-test',
            ARCH,
            'prowebsite.seo_batch1_arch_test',
        )
        field = view._fields['arch_db']
        en_terms = field.get_trans_terms(view.with_context(lang='en_US').arch_db)
        lead = next(term for term in en_terms if YEAR_OLD in term)
        ark = next(term for term in en_terms if ARK_OLD in term)
        view.update_field_translations('arch_db', {
            'fr_CA': {
                lead: 'revendeur autorise depuis 2020 partenaire Diamant',
                ark: 'scanner BLK ARK',
            },
            'es_ES': {
                lead: 'revendedor autorizado desde 2020 Diamond Partner',
                ark: 'escaner BLK ARK',
            },
        })

        first_year = replace_arch_substring(view, YEAR_OLD, YEAR_NEW, langs=['en_US'])
        self.assertGreater(first_year.get('en_US', {}).get('terms', 0), 0)
        self.assertNotIn('fr_CA', first_year)
        self.assertNotIn('es_ES', first_year)
        en_arch = view.with_context(lang='en_US').arch_db
        fr_arch = view.with_context(lang='fr_CA').arch_db
        es_arch = view.with_context(lang='es_ES').arch_db
        self.assertIn(YEAR_NEW, en_arch)
        self.assertNotIn(YEAR_OLD, en_arch)
        self.assertIn('depuis 2020', fr_arch)
        self.assertIn('desde 2020', es_arch)
        self.assertNotIn(YEAR_OLD, fr_arch)
        self.assertNotIn(YEAR_NEW, fr_arch)

        second_year = replace_arch_substring(view, YEAR_OLD, YEAR_NEW, langs=['en_US'])
        self.assertFalse(second_year)
        self.assertEqual(view.with_context(lang='en_US').arch_db, en_arch)
        self.assertEqual(view.with_context(lang='fr_CA').arch_db, fr_arch)

        first_ark = replace_arch_substring(view, ARK_OLD, ARK_NEW)
        self.assertGreater(first_ark.get('en_US', {}).get('terms', 0), 0)
        self.assertGreater(first_ark.get('fr_CA', {}).get('terms', 0), 0)
        self.assertGreater(first_ark.get('es_ES', {}).get('terms', 0), 0)
        for lang in ('en_US', 'fr_CA', 'es_ES'):
            arch = view.with_context(lang=lang).arch_db
            self.assertNotIn(ARK_OLD, arch, lang)
            self.assertIn(ARK_NEW, arch, lang)
        # The French and Spanish year sentences are still the translated ones.
        self.assertIn('depuis 2020', view.with_context(lang='fr_CA').arch_db)
        self.assertIn('desde 2020', view.with_context(lang='es_ES').arch_db)

        second_ark = replace_arch_substring(view, ARK_OLD, ARK_NEW)
        self.assertFalse(second_ark)

    def test_year_helper_does_nothing_when_the_phrase_is_absent(self):
        view, _page = self._view_and_page(
            '/seo-batch1-no-year',
            '<div><p>No year in this paragraph.</p></div>',
            'prowebsite.seo_batch1_no_year',
        )
        before = view.with_context(lang='en_US').arch_db
        self.assertFalse(replace_arch_substring(view, YEAR_OLD, YEAR_NEW, langs=['en_US']))
        self.assertEqual(view.with_context(lang='en_US').arch_db, before)

    def test_sitemap_cache_delete_is_limited_to_website_1_and_idempotent(self):
        Attachment = self.env['ir.attachment']
        keep = Attachment.create({
            'name': '/sitemap-2-abcd1234.xml',
            'url': '/sitemap-2-abcd1234.xml',
            'type': 'binary',
            'mimetype': 'application/xml',
            'datas': base64.b64encode(b'<urlset/>'),
        })
        drop_names = (
            '/sitemap-1-abcd1234.xml',
            '/sitemap-1-abcd1234-2.xml',
        )
        for url in drop_names:
            Attachment.create({
                'name': url,
                'url': url,
                'type': 'binary',
                'mimetype': 'application/xml',
                'datas': base64.b64encode(b'<urlset/>'),
            })
        self.assertEqual(clear_sitemap_attachments(self.env, 1), 2)
        self.assertTrue(keep.exists())
        self.assertFalse(Attachment.search([('url', 'in', list(drop_names))]))
        self.assertEqual(clear_sitemap_attachments(self.env, 1), 0)

    def test_full_migrate_can_run_twice(self):
        for url, key in (
            ('/dev', 'prowebsite.seo_batch1_dev'),
            ('/cont', 'prowebsite.seo_batch1_cont'),
            ('/telechargement', 'prowebsite.seo_batch1_telechargement'),
        ):
            if not self.env['website.page'].search([('url', '=', url), ('website_id', '=', 1)]):
                self._view_and_page(url, '<div/>', key)

        first = migrate_seo_batch1(self.env)
        self.env.invalidate_all()
        second = migrate_seo_batch1(self.env)
        self.env.invalidate_all()

        self.assertEqual(first['spanish_code'], 'es_ES')
        self.assertTrue(first['robots_exact'])
        self.assertTrue(second['robots_exact'])
        self.assertEqual(str(self.website.robots_txt), ROBOTS_TXT)
        self.assertEqual(self._terms_rewritten(second['blk_ark']), 0)
        self.assertEqual(self._terms_rewritten(second['year']), 0)
        pages = self.env['website.page'].search([
            ('url', 'in', ['/dev', '/cont', '/telechargement']),
            '|', ('website_id', '=', 1), ('website_id', '=', False),
        ])
        self.assertTrue(pages)
        self.assertFalse(any(pages.mapped('website_indexed')))

        for url, meta in PAGE_META.items():
            page = self.env['website.page'].search([
                ('url', '=', url), ('website_id', '=', 1),
            ], limit=1)
            if not page:
                self.assertFalse(second['pages'][url]['found'])
                continue
            self.assertEqual(
                page.with_context(lang='en_US').website_meta_title,
                meta['en_US'][0],
            )


@tagged('post_install', '-at_install')
class TestSitemapOverride(TransactionCase):

    def test_prefix_filter_on_the_website_model(self):
        website = self.env['website'].browse(1)
        if not website.exists():
            website = self.env['website'].search([], limit=1)
        self.assertTrue(website._seo_batch1_skip_loc('/dev'))
        self.assertTrue(website._seo_batch1_skip_loc('/cont'))
        self.assertTrue(website._seo_batch1_skip_loc('/blog/news-2/feed'))
        self.assertFalse(website._seo_batch1_skip_loc('/contact-us'))
        self.assertFalse(website._seo_batch1_skip_loc('/contact-information-form'))
        self.assertFalse(website._seo_batch1_skip_loc('/devices'))
        self.assertFalse(website._seo_batch1_skip_loc('/rental/scanners'))
        self.assertFalse(website._seo_batch1_skip_loc('/rental/scanners/blkarc'))
        self.assertFalse(website._seo_batch1_skip_loc('/blog'))
        self.assertFalse(website._seo_batch1_skip_loc('/blog/news-2'))
        self.assertFalse(website._seo_batch1_skip_loc('/appointment'))
        self.assertFalse(website._seo_batch1_skip_loc('/capture/software/cloudworx'))

    def test_duplicate_blog_post_urls_follow_blog_id(self):
        if 'blog.post' not in self.env:
            self.skipTest('website_blog is not installed')
        website = self.env['website'].search([], limit=1)
        news = self.env['blog.blog'].create({'name': 'News'})
        hardware = self.env['blog.blog'].create({'name': 'Hardware'})
        post = self.env['blog.post'].create({
            'name': 'New office',
            'blog_id': news.id,
        })
        from odoo.addons.http_routing.models.ir_http import slug
        canonical = '/blog/%s/%s' % (slug(news), slug(post))
        duplicate = '/blog/%s/%s' % (slug(hardware), slug(post))
        self.assertFalse(website._seo_batch1_skip_loc(canonical))
        self.assertTrue(website._seo_batch1_skip_loc(duplicate))
        self.assertFalse(website._seo_batch1_skip_loc('/blog/%s' % slug(news)))
        self.assertFalse(website._seo_batch1_skip_loc('/blog'))
