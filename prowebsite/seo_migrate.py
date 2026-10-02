# -*- coding: utf-8 -*-
"""Idempotent content updates for the first SEO batch.

Odoo 17 specifics used here (check these on a later port):

- Translated HTML/XML (``ir.ui.view.arch_db``, ``translate=xml_translate``)
  is updated with ``update_field_translations(field, {lang: {old_term: new_term}})``.
  The dict key is the full translatable term, not a bare substring. A plain
  ``write`` of ``arch_db`` replaces the English source and can detach the
  other languages.
- ``website_meta_title`` / ``website_meta_description`` are ``translate=True``
  (one string per language). ``with_context(lang=...).write`` updates that
  language only. ``get_website_meta`` copies those two fields into
  ``og:title`` / ``og:description`` and the twitter tags. There is no stored
  og:title field. ``website_meta_og_img`` is not translated.
- Odoo 17 ``website.layout`` already emits
  ``<meta name="robots" content="noindex"/>`` when
  ``main_object.website_indexed`` is false. No layout change is required for
  the stub pages.
- ``/robots.txt`` renders ``website.robots`` (one ``User-agent: *`` plus
  ``Sitemap:``) and then ``website.robots_txt``. ``Website`` inherits
  ``web.controllers.home.Home``. That controller appends a second
  ``User-agent: *`` only when ``_get_allowed_robots_routes`` returns paths.
  The base implementation returns ``[]``.
- Cached sitemap attachments are named by ``sitemap_xml_index`` as
  ``/sitemap-<website_id>-<md5(url_root)[:8]>.xml`` (and ``-N`` before a
  single-page file is renamed).
- Post-migrate entry point is ``migrate(cr, version)`` and
  ``api.Environment(cr, SUPERUSER_ID, {})``.
"""
import logging

from odoo import api, SUPERUSER_ID

from odoo.addons.prowebsite.seo_batch1_data import (
    ARK_NEW,
    ARK_OLD,
    PAGE_META,
    ROBOTS_TXT,
    UNINDEXED_URLS,
    WEBSITE_ID,
    YEAR_NEW,
    YEAR_OLD,
)

_logger = logging.getLogger(__name__)


def active_spanish_code(env):
    """Return the active ``es_*`` language code, preferring ``es_ES``.

    The public site uses ``/es/`` and ``html lang="es-ES"``. The active
    ``res.lang`` row is what ``with_context(lang=...)`` must use.
    """
    Lang = env['res.lang'].sudo()
    langs = Lang.search([('active', '=', True), ('code', '=like', 'es_%')])
    if not langs:
        return None
    codes = set(langs.mapped('code'))
    if 'es_ES' in codes:
        return 'es_ES'
    if 'url_code' in Lang._fields:
        by_url = langs.filtered(lambda lang: lang.url_code == 'es')
        if len(by_url) == 1:
            return by_url.code
    return langs[0].code


def _installed_lang_codes(env):
    codes = {code for code, _name in env['res.lang'].get_installed()}
    # en_US is the source language for translated fields even when the
    # website's language list is checked a different way.
    codes.add('en_US')
    return codes


def _pages_for_website(env, url, website_id):
    Page = env['website.page'].sudo().with_context(active_test=False)
    return Page.search([('url', '=', url), ('website_id', '=', website_id)])


def _clear_stale_og_image(page):
    """Drop an og:image whose URL still carries the cloned tripods title or the ARK typo.

    ``og:title`` and ``og:description`` are not stored; they follow the SEO
    fields. ``website_meta_og_img`` is stored and is not translated.
    """
    image = page.website_meta_og_img or ''
    lowered = image.lower()
    if 'tripod' in lowered or ARK_OLD in image:
        page.write({'website_meta_og_img': False})
        return image
    return None


def apply_page_meta(env, page, meta_by_lang, spanish_code):
    """Write title and description for one page. Safe to call again."""
    installed = _installed_lang_codes(env)
    lang_codes = {
        'en_US': 'en_US',
        'fr_CA': 'fr_CA',
        'es': spanish_code,
    }
    applied = []
    skipped = []
    for key, (title, description) in meta_by_lang.items():
        code = lang_codes.get(key)
        if not code or code not in installed:
            skipped.append(key)
            continue
        page.with_context(lang=code).write({
            'website_meta_title': title,
            'website_meta_description': description,
        })
        applied.append(code)
    cleared = _clear_stale_og_image(page)
    return {'applied': applied, 'skipped': skipped, 'og_img_cleared': bool(cleared), 'og_img_was': cleared}


def _term_mapping(field, value, old, new):
    """Map full translatable terms that contain ``old`` onto the replaced text.

    Returns ``(mapping, split)``. ``split`` is true when ``old`` is in the
    arch but not inside a single term (the year or the typo is broken across
    tags). Those arches are left unchanged: rewriting the whole arch would
    drop the other languages.
    """
    if not value or not isinstance(value, str) or old not in value:
        return {}, False
    mapping = {}
    for term in field.get_trans_terms(value):
        if old in term:
            mapping[term] = term.replace(old, new)
    return mapping, not mapping


def replace_arch_substring(view, old, new, langs=None):
    """Replace ``old`` with ``new`` in ``arch_db`` for the given languages.

    ``langs`` None means every language that has its own stored arch. Only
    stored translations are written. A language that merely falls back to
    en_US is not copied, so it keeps following the English arch.
    """
    field = view._fields['arch_db']
    stored = field._get_stored_translations(view) or {}
    translations = {}
    report = {}
    for lang, value in stored.items():
        if not lang or lang.startswith('_'):
            continue
        if langs is not None and lang not in langs:
            continue
        mapping, split = _term_mapping(field, value, old, new)
        if not mapping and not split:
            continue
        report[lang] = {
            'terms': len(mapping),
            'occurrences': value.count(old) if isinstance(value, str) else 0,
            'split': split,
        }
        if mapping:
            translations[lang] = mapping
    if translations:
        view.update_field_translations('arch_db', translations)
    return report


def _homepage_views(env, website):
    Page = env['website.page'].sudo().with_context(active_test=False)
    pages = Page.search([
        ('url', '=', '/'),
        '|', ('website_id', '=', website.id), ('website_id', '=', False),
    ])
    specific_pages = pages.filtered(lambda page: page.website_id.id == website.id)
    views = (specific_pages or pages).view_id
    homepage = website.with_context(website_id=website.id).viewref(
        'website.homepage', raise_if_not_found=False,
    )
    if homepage:
        views |= homepage
    # Prefer the website-specific view when both the generic and the copy
    # contain the phrase, so a shared homepage is not rewritten for every site.
    def _has_phrase(view):
        arch = view.with_context(lang='en_US').arch_db or ''
        return YEAR_OLD in arch

    specific = views.filtered(lambda view: view.website_id.id == website.id and _has_phrase(view))
    if specific:
        return specific
    return views.filtered(_has_phrase)


def clear_sitemap_attachments(env, website_id):
    """Delete cached sitemap files for one website.

    ``website/controllers/main.py`` ``sitemap_xml_index`` stores them as
    ``/sitemap-<id>-<hash>.xml`` and, while generating, ``/sitemap-<id>-<hash>-<n>.xml``.
    """
    Attachment = env['ir.attachment'].sudo()
    attachments = Attachment.search([
        ('type', '=', 'binary'),
        ('url', '=like', '/sitemap-%s-%%.xml' % website_id),
    ])
    count = len(attachments)
    if attachments:
        attachments.unlink()
    return count


def migrate_seo_batch1(env):
    """Apply meta, robots, noindex, arch fixes and sitemap-cache invalidation.

    Missing records are logged and skipped so a rebuild still upgrades the
    module. Running this again writes the same values and does not touch an
    arch that no longer contains the old phrase.
    """
    env = env(su=True)
    report = {
        'website_id': WEBSITE_ID,
        'pages': {},
        'blk_ark': {},
        'year': {},
        'unindexed': [],
        'unindexed_missing': [],
        'sitemap_attachments_deleted': 0,
    }
    website = env['website'].browse(WEBSITE_ID).exists()
    if not website:
        _logger.warning('seo batch1: website id %s was not found; nothing written', WEBSITE_ID)
        report['website_missing'] = True
        return report

    spanish = active_spanish_code(env)
    report['spanish_code'] = spanish
    if not spanish:
        _logger.warning('seo batch1: no active es_* language; Spanish meta was skipped')

    for url, meta in PAGE_META.items():
        pages = _pages_for_website(env, url, website.id)
        if not pages:
            others = env['website.page'].sudo().with_context(active_test=False).search([('url', '=', url)])
            other_ids = [(page.id, page.website_id.id or False) for page in others]
            _logger.warning(
                'seo batch1: no website.page url=%s website_id=%s (matches: %s)',
                url, website.id, other_ids,
            )
            report['pages'][url] = {'found': False, 'matches': other_ids}
            continue
        page_reports = []
        for page in pages:
            page_reports.append(apply_page_meta(env, page, meta, spanish))
            if url == '/rental/scanners/blkarc' and page.view_id:
                ark_report = replace_arch_substring(page.view_id, ARK_OLD, ARK_NEW)
                report['blk_ark'][page.view_id.id] = ark_report
                _logger.info(
                    'seo batch1: BLK ARK scan on view %s url=%s: %s',
                    page.view_id.id, url, ark_report or 'no BLK ARK in stored arch translations',
                )
        report['pages'][url] = {'found': True, 'ids': pages.ids, 'writes': page_reports}

    if str(website.robots_txt or '') != ROBOTS_TXT:
        website.write({'robots_txt': ROBOTS_TXT})
        website.invalidate_recordset(['robots_txt'])
    if str(website.robots_txt or '') != ROBOTS_TXT:
        _logger.warning('seo batch1: ORM did not store robots_txt exactly; writing the column directly')
        env.cr.execute(
            'UPDATE website SET robots_txt = %s WHERE id = %s',
            (ROBOTS_TXT, website.id),
        )
        website.invalidate_recordset(['robots_txt'])
    report['robots_exact'] = str(website.robots_txt or '') == ROBOTS_TXT

    Page = env['website.page'].sudo().with_context(active_test=False)
    stubs = Page.search([
        ('url', 'in', list(UNINDEXED_URLS)),
        '|', ('website_id', '=', website.id), ('website_id', '=', False),
    ])
    if stubs:
        stubs.write({'website_indexed': False})
    found_urls = set(stubs.mapped('url'))
    report['unindexed'] = sorted(found_urls)
    report['unindexed_missing'] = [url for url in UNINDEXED_URLS if url not in found_urls]
    if report['unindexed_missing']:
        _logger.warning('seo batch1: stub pages not found: %s', report['unindexed_missing'])

    year_views = _homepage_views(env, website)
    if not year_views:
        _logger.info('seo batch1: %r was not found on the website %s homepage; year left unchanged', YEAR_OLD, website.id)
    for view in year_views:
        year_report = replace_arch_substring(view, YEAR_OLD, YEAR_NEW, langs=['en_US'])
        report['year'][view.id] = year_report
        _logger.info('seo batch1: homepage year on view %s: %s', view.id, year_report or 'phrase not in en_US')

    report['sitemap_attachments_deleted'] = clear_sitemap_attachments(env, website.id)
    _logger.info('seo batch1: done %s', {
        'spanish_code': spanish,
        'pages': {url: data.get('found') for url, data in report['pages'].items()},
        'blk_ark': report['blk_ark'],
        'year': report['year'],
        'unindexed': report['unindexed'],
        'unindexed_missing': report['unindexed_missing'],
        'robots_exact': report['robots_exact'],
        'sitemap_attachments_deleted': report['sitemap_attachments_deleted'],
    })
    return report


def migrate(cr, version):
    """Entry point used by migrations/<version>/post-migrate.py."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    migrate_seo_batch1(env)
