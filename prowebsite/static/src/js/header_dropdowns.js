/** @odoo-module **/
import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

// ─────────────────────────────────────────────────────────────────────────────
// Top-level nav menus rebuilt into the custom hover bar, same as account/lang.
// `label` is matched case-insensitively against the top-level link's own text
// (there's no stable id/class for these — they're ordinary website.menu
// entries), so a site-owner rename in the Website > Menu editor will just
// leave that one item on its native dropdown instead of breaking anything.
// ─────────────────────────────────────────────────────────────────────────────
const MEGA_MENU_ITEMS = [
    { key: 'equipment',   label: 'equipment' },
    { key: 'software',    label: 'software' },
    { key: 'accessories', label: 'accessories' },
    { key: 'rentals',     label: 'rentals' },
    { key: 'resources',   label: 'resources' },
];

/** Find the top-level nav <li> whose own link text matches `label`. */
function findTopLevelMenuLi(headerEl, label) {
    const topMenu = headerEl.querySelector('#top_menu') || document.querySelector('#top_menu');
    if (!topMenu) return null;
    return Array.from(topMenu.children).find(li => {
        const link = li.querySelector(':scope > a');
        return link && link.textContent.trim().toLowerCase() === label;
    }) || null;
}

/**
 * Walk a menu item's own dropdown/mega-menu content and group its links under
 * whatever heading-like element precedes them. Written generically (rather
 * than assuming one exact markup) because the real content lives in the
 * website's menu configuration in the database — it could be a plain 2-level
 * website.submenu (Odoo's default) or a full custom mega_menu_content HTML
 * blob, and this needs to produce something sane either way.
 */
function extractMenuColumns(li) {
    if (!li) return [];
    const root = li.querySelector(':scope > ul.dropdown-menu, :scope > .o_mega_menu, :scope > .dropdown-menu');
    if (!root) return [];

    const HEADING_TAGS = new Set(['H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'STRONG', 'B']);

    function isGroupToggle(el) {
        // A dropdown-toggle only counts as a column heading if it has a sibling
        // dropdown-menu under the same <li> — i.e. it's a group, not a leaf link
        // that merely happens to carry the same class.
        return el.tagName === 'A'
            && el.classList.contains('dropdown-toggle')
            && !!el.parentElement?.querySelector(':scope > ul.dropdown-menu, :scope > .dropdown-menu');
    }

    const columns = [];
    let current = null;

    function pushItem(label, href) {
        label = label.trim();
        if (!label) return;
        if (!current) {
            current = { label: '', items: [] };
            columns.push(current);
        }
        current.items.push({ href: href || '#', label });
    }

    function walk(node) {
        Array.from(node.children).forEach(child => {
            if (isGroupToggle(child)) {
                current = { label: child.textContent.trim(), items: [] };
                columns.push(current);
                return; // its sibling <ul> is handled on the next iteration
            }
            if (child.tagName === 'A') {
                pushItem(child.textContent, child.getAttribute('href'));
                return;
            }
            if (HEADING_TAGS.has(child.tagName)) {
                current = { label: child.textContent.trim(), items: [] };
                columns.push(current);
                return;
            }
            walk(child); // recurse through wrapper <li>/<ul>/<div>/<row>/<col> elements
        });
    }

    walk(root);
    return columns.filter(col => col.items.length);
}

function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

function renderMenuColumnHTML(col) {
    return `
        <div class="o_hdd_menu_col">
            ${col.label ? `<p class="o_hdd_menu_col_label">${escapeHtml(col.label)}</p>` : ''}
            <ul class="o_hdd_menu_col_items">
                ${col.items.map(item => `
                    <li>
                        <a href="${escapeHtml(item.href)}" class="o_hdd_menu_link">
                            <span class="o_hdd_menu_link_text">${escapeHtml(item.label)}</span>
                            <svg class="o_hdd_menu_link_arrow" width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
                        </a>
                    </li>
                `).join('')}
            </ul>
        </div>
    `;
}

/** Featured product cards for the Accessories panel — hand-authored, since
 *  these promote specific products rather than mirroring a plain link list.
 *  Update the image src / href here if the URLs change.
 *  Images: OmniGO uses the actual product photo already used elsewhere in
 *  this codebase (the "Introducing OmniGO" notification popup), rather than
 *  the plain header wordmark — reads much better at this card size. Omni360
 *  still uses its wordmark (Omni360.png) as a placeholder — swap for a real
 *  product photo of the physical adapter once one exists; the card's dark
 *  background (see .o_hdd_feature_card in header_dropdowns.css) now has
 *  enough contrast for either a red-and-white logo or a photo either way. */
const ACCESSORIES_FEATURED_CARDS = `
    <a href="/omnigo" class="o_hdd_feature_card">
        <div class="o_hdd_feature_card_media">
            <img src="https://cdn.r-e-a-l.it/images/ecommerce/OmniGO2.png" alt="OmniGO"/>
        </div>
        <p class="o_hdd_feature_card_kicker">Multi-Scanner Adapter</p>
        <p class="o_hdd_feature_card_name">OmniGO</p>
        <span class="o_hdd_feature_card_cta">Check out the OmniGO
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
        </span>
    </a>
    <a href="/omni360" class="o_hdd_feature_card o_hdd_feature_card--new">
        <span class="o_hdd_feature_card_badge">New</span>
        <div class="o_hdd_feature_card_media">
            <img src="https://cdn.r-e-a-l.it/images/ecommerce/Omni360.png" alt="Omni360"/>
        </div>
        <p class="o_hdd_feature_card_kicker">Multi-Scanner Adapter</p>
        <p class="o_hdd_feature_card_name">Omni360</p>
        <span class="o_hdd_feature_card_cta">Check out the Omni360
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m13 6 6 6-6 6"/></svg>
        </span>
    </a>
`;

function renderMenuPanelHTML(key, columns) {
    const isAccessories = key === 'accessories';
    return `
        <div class="o_hdd_panel" data-panel="${key}">
            <div class="o_hdd_menu_inner${isAccessories ? ' o_hdd_menu_inner--accessories' : ''}">
                ${isAccessories ? `<div class="o_hdd_feature_cards">${ACCESSORIES_FEATURED_CARDS}</div>` : ''}
                <div class="o_hdd_menu_cols${isAccessories ? ' o_hdd_menu_cols--secondary' : ''}">
                    ${columns.map(renderMenuColumnHTML).join('')}
                </div>
            </div>
        </div>
    `;
}

// ─────────────────────────────────────────────────────────────────────────────
// initHeaderDropdowns(headerEl, iconsUl)
//
// Core function that creates the full-width dropdown bar for ANY header.
// Called from:
//   • The publicWidget below  (normal Odoo pages, standard #top header)
//   • three_product.js        (OmniGO custom header, after icon injection)
// ─────────────────────────────────────────────────────────────────────────────
export function initHeaderDropdowns(headerEl, iconsUl) {
    const accountLi = iconsUl.querySelector('li.dropdown.o_no_autohide_item');
    const langLi    = iconsUl.querySelector('li.o_header_language_selector');
    if (!accountLi && !langLi) return;

    // ── Extract account items from the existing Odoo dropdown ─────────────
    const accountItems = accountLi
        ? Array.from(accountLi.querySelectorAll('.dropdown-item')).map(a => ({
            href:  a.getAttribute('href') || '#',
            icon:  a.querySelector('i')?.className || '',
            label: a.textContent.trim(),
          }))
        : [];

    // ── Extract language items from the existing Odoo dropdown ────────────
    const langAnchors = langLi
        ? Array.from(langLi.querySelectorAll('.js_change_lang'))
        : [];

    const langItems = langAnchors.map(a => ({
        href:   a.getAttribute('href') || '#',
        code:   a.dataset.url_code || '',
        label:  a.querySelector('span')?.textContent.trim()
                  || (a.dataset.url_code || '').toUpperCase(),
        active: a.classList.contains('active'),
    }));

    // ── Locate + extract the 5 plain nav menus (Equipment, Software, ...) ──
    // Each entry pairs its matched <li> (or null if this header/page doesn't
    // have that menu — e.g. the OmniGO/Omni360 custom header) with the
    // columns extracted from whatever dropdown/mega-menu content it has.
    const megaMenus = MEGA_MENU_ITEMS.map(({ key, label }) => {
        const li = findTopLevelMenuLi(headerEl, label);
        let columns = extractMenuColumns(li);
        if (key === 'accessories') {
            // The featured OmniGO/Omni360 cards above already cover both
            // products prominently — drop the server-side "OmniGO adapter
            // for BLK2GO" column (extracted from the actual mega-menu
            // content in the database) so it isn't duplicated as a smaller,
            // OmniGO-only column right next to them. That heading text lives
            // in Odoo's own menu editor, not here, so it can't be renamed
            // from code — but filtering it out achieves the same end result.
            columns = columns.filter(col => !/omnigo/i.test(col.label));
        }
        return { key, li, columns };
    });

    // ── Build the dropdown bar ─────────────────────────────────────────────
    const bar = document.createElement('div');
    bar.className = 'o_hdd_bar';
    bar.innerHTML = `
        <div class="o_hdd_panel" data-panel="account">
            <div class="o_hdd_account_inner">
                ${accountItems.map(item => `
                    <a href="${item.href}" class="o_hdd_acct_link">
                        <i class="${item.icon}"></i>
                        <span>${item.label}</span>
                    </a>
                `).join('')}
            </div>
        </div>
        <div class="o_hdd_panel" data-panel="lang">
            <div class="o_hdd_lang_map"></div>
            <div class="o_hdd_lang_options">
                <div class="o_hdd_col">
                    <p class="o_hdd_col_label">Language</p>
                    <div class="o_hdd_col_items">
                        ${langItems.map(item => `
                            <a href="${item.href}"
                               class="o_hdd_pill${item.active ? ' is-active' : ''}"
                               data-url_code="${item.code}">
                                ${item.label}
                            </a>
                        `).join('')}
                    </div>
                </div>
                <div class="o_hdd_col_divider" data-cur-divider></div>
                <div class="o_hdd_col" data-cur-col>
                    <p class="o_hdd_col_label">Currency</p>
                    <div class="o_hdd_col_items" data-cur-items>
                        <span class="o_hdd_loading">…</span>
                    </div>
                </div>
            </div>
        </div>
        ${megaMenus.filter(m => m.li).map(m => renderMenuPanelHTML(m.key, m.columns)).join('')}
    `;

    // Always append to body — position:fixed handles placement
    document.body.appendChild(bar);

    // ── Delegate language pill clicks to original Odoo anchors ────────────
    // Language is INDEPENDENT of currency (the store's languages are
    // English / fr_CA / es don't map to a currency). Copying the href alone
    // doesn't work for all languages: the default language often has href="" on
    // its .js_change_lang element, which our || '#' fallback turns into a no-op
    // anchor. Delegating to the original element ensures Odoo's own routing runs.
    const langAnchorsByCode = new Map(langAnchors.map(a => [a.dataset.url_code || '', a]));
    bar.querySelectorAll('[data-panel="lang"] .o_hdd_pill').forEach(pill => {
        const orig = langAnchorsByCode.get(pill.dataset.url_code || '');
        if (orig) {
            pill.addEventListener('click', e => {
                e.preventDefault();
                orig.click();
            });
        }
    });

    // ── Currency switcher (universal: this runs on every header) ──────────
    // Writes a `pl_region` cookie (US/CA) and reloads. The server
    // (proproduct/models/website.py) resolves the matching pricelist by its
    // exact flag-emoji name; when the cookie is absent it falls back to geo-IP.
    // A full reload re-renders all server-side prices (product page + OmniGO).
    function setCurrencyRegion(region) {
        document.cookie = `pl_region=${region};path=/;max-age=31536000;SameSite=Lax`;
        console.log("[proproduct] currency switch clicked -> set pl_region cookie:", region,
            "| document.cookie now:", document.cookie);
        window.location.reload();
    }

    const curItems   = bar.querySelector('[data-cur-items]');
    const curCol      = bar.querySelector('[data-cur-col]');
    const curDivider  = bar.querySelector('[data-cur-divider]');
    function hideCurrency() {
        if (curCol)     curCol.style.display = 'none';
        if (curDivider) curDivider.style.display = 'none';
    }
    jsonrpc('/omnigo/get_pricelists', {}).then(list => {
        if (!Array.isArray(list) || list.length < 2 || !curItems) {
            hideCurrency();   // nothing meaningful to switch between
            return;
        }
        curItems.innerHTML = list.map(pl => `
            <a href="#"
               class="o_hdd_pill${pl.active ? ' is-active' : ''}"
               data-region="${pl.label}">
                ${pl.flag} ${pl.currency}
            </a>
        `).join('');
        curItems.querySelectorAll('.o_hdd_pill').forEach(pill => {
            pill.addEventListener('click', e => {
                e.preventDefault();
                setCurrencyRegion(pill.dataset.region);
            });
        });
    }).catch(hideCurrency);

    // ── Keep bar pinned to the bottom edge of the header ──────────────────
    // Uses the header's actual on-screen bottom edge (getBoundingClientRect),
    // not just its height — offsetHeight alone only catches size changes
    // (e.g. the glass shrink-on-scroll), not the header's on-screen *position*
    // changing, which can happen independently (e.g. Odoo's own header scroll
    // effects). Recomputed on both resize and scroll so the bar's border never
    // freezes at a stale offset while the header itself moves around it.
    let _barTopRaf = null;
    function updateBarTop() {
        if (_barTopRaf) return;
        _barTopRaf = requestAnimationFrame(() => {
            _barTopRaf = null;
            bar.style.top = headerEl.getBoundingClientRect().bottom + 'px';
        });
    }
    updateBarTop();
    new ResizeObserver(updateBarTop).observe(headerEl);
    (document.getElementById('wrapwrap') || window).addEventListener('scroll', updateBarTop, { passive: true });
    window.addEventListener('resize', updateBarTop, { passive: true });

    // ── Hover wiring ───────────────────────────────────────────────────────
    let _hideTimer = null;

    function showPanel(name) {
        clearTimeout(_hideTimer);
        bar.querySelectorAll('.o_hdd_panel').forEach(p => {
            p.classList.toggle('is-visible', p.dataset.panel === name);
        });
        bar.classList.add('is-open');
    }

    function scheduleHide() {
        _hideTimer = setTimeout(() => {
            bar.classList.remove('is-open');
            bar.querySelectorAll('.o_hdd_panel').forEach(p => p.classList.remove('is-visible'));
        }, 140);
    }

    function wire(li, panelName) {
        if (!li) return;
        li.addEventListener('mouseenter', () => showPanel(panelName));
        li.addEventListener('mouseleave', scheduleHide);
    }

    wire(accountLi, 'account');
    wire(langLi,    'lang');

    // Wire the 5 rebuilt nav menus the same way. Each matched <li> gets
    // `o_hdd_wired` so the CSS rule below can hide its native dropdown/mega-menu
    // at desktop widths — only for menus we actually found and rebuilt, so a
    // renamed menu just keeps working as a normal native dropdown instead of
    // silently losing its content.
    megaMenus.forEach(({ key, li }) => {
        if (!li) return;
        li.classList.add('o_hdd_wired');
        wire(li, key);
    });

    bar.addEventListener('mouseenter', () => clearTimeout(_hideTimer));
    bar.addEventListener('mouseleave', scheduleHide);

    // Signal that the custom hover bar is live, so CSS can suppress the native
    // Bootstrap account/language menus (only when the bar actually built).
    document.body.classList.add('o_hdd_active');
}

// ─────────────────────────────────────────────────────────────────────────────
// buildSiteHeader(nativeHeaderEl)
//
// Replaces the native desktop header with a purpose-built one, the same
// approach three_product.js already uses for the Omni pages. Whether it
// floats (fixed, glassy, no page-content compensation) or sits normally
// in-flow is decided per page by reading the SAME header_overlay preference
// Odoo's own page-customize panel already stores (reflected as
// #wrapwrap.o_header_overlay) — pages like RTC/Omni/the homepage have that
// enabled *and* a hero section built with its own top padding (e.g. pt176)
// specifically to make room for a floating header; pages without either
// (checkout, cart, wishlist, etc.) get the plain in-flow layout instead, so
// nothing ever gets covered. No body-padding compensation is added in either
// case — that fights the per-hero spacing model these pages already use
// instead of matching it.
// ─────────────────────────────────────────────────────────────────────────────
function buildSiteHeader(nativeHeaderEl) {
    // Desktop nav only — website.template_header_mobile renders a separate
    // <nav aria-label="Mobile"> sibling for the offcanvas menu, which is
    // left completely untouched.
    const desktopNav = nativeHeaderEl.querySelector('nav[aria-label="Main"]');
    if (!desktopNav) return null;

    const brand = desktopNav.querySelector('.navbar-brand');
    const topMenu = desktopNav.querySelector('#top_menu');
    const iconsUl =
        desktopNav.querySelector('ul.o_header_sales_one_right_col')
        || desktopNav.querySelector('.o_header_language_selector')?.closest('ul');

    // Any of these missing means the native header isn't shaped the way this
    // function expects (e.g. a page-specific header override) — bail out and
    // leave the native header exactly as Odoo rendered it, rather than build
    // a half-populated replacement.
    if (!brand || !topMenu || !iconsUl) return null;

    const header = document.createElement('header');
    // Two signals, either is enough: Odoo's own per-page "Header Position:
    // Over The Content" builder flag (#wrapwrap.o_header_overlay) — OR the
    // page actually having a full-bleed hero to overlay in the first place.
    // The flag alone isn't reliable: pages like the RTC series predate this
    // system entirely and were built around their own hero design (e.g. a
    // deliberate 176px top padding reserved for a floating header) without
    // ever having that native per-page setting turned on.
    const wantsOverlay =
        document.getElementById('wrapwrap')?.classList.contains('o_header_overlay')
        || !!document.querySelector('#wrap .s_cover.o_full_screen_height');
    header.className = 'o_site_header' + (wantsOverlay ? ' o_site_header--overlay' : '');
    header.innerHTML = `
        <div class="o_site_header_inner">
            <div class="o_site_header_left"></div>
            <nav class="o_site_header_nav" aria-label="Main"></nav>
            <div class="o_site_header_right"></div>
        </div>
    `;

    // Relocate (not clone) — every native Bootstrap/Odoo binding on these
    // elements (dropdown toggles, search modal trigger, cart badge, language
    // switcher, mega-menu dropdown wiring added below) travels with them.
    header.querySelector('.o_site_header_left').appendChild(brand);
    header.querySelector('.o_site_header_nav').appendChild(topMenu);
    header.querySelector('.o_site_header_right').appendChild(iconsUl);

    document.body.prepend(header);

    // desktopNav is now an empty shell (its meaningful children were just
    // relocated above), but its own box (padding, the .container inside it,
    // possibly a second "Bottom" row for text/social links) still renders —
    // an empty but still-sized bar. The CSS rule that hides it pre-JS
    // (header#top nav[aria-label="Main"] {...} in header_dropdowns.css)
    // stops matching the instant the id="top" strip below runs, since it's
    // an ID selector — so it must also be hidden directly, here, in a way
    // that doesn't depend on any selector that could later stop matching.
    desktopNav.style.setProperty('display', 'none', 'important');

    // The native mobile nav (a <nav aria-label="Mobile"> sibling of
    // desktopNav, still inside nativeHeaderEl) is deliberately left exactly
    // where it is — untouched, still fully functional. It's already only
    // visible below 992px via its own native d-lg-none class, so it stays
    // invisible on desktop without any help from this code, and there's no
    // reason to relocate something that's already correctly self-hiding.

    // Strip id="top" so nothing can match this element by ID going forward
    // (CSS #top {...} rules, document.getElementById('top'), etc.) — but
    // leave the element itself attached to the DOM, still containing the
    // native mobile nav. Odoo's own core header-affix widget (unrelated to
    // this module, part of the website addon's own JS bundle) is already
    // bound to this exact element by the time this code runs. A previous
    // version of this function called nativeHeaderEl.remove() instead, which
    // left that widget holding a reference into a now-detached subtree —
    // every scroll/resize tick after that it tried to resolve an ancestor
    // chain that no longer existed and threw ("scrollableEl.matches is not
    // a function", scrollableEl undefined) continuously. Keeping the node
    // attached (now empty on desktop, id-less, visually inert) keeps that
    // widget's internal references valid, so it just quietly does nothing
    // instead of erroring.
    nativeHeaderEl.removeAttribute('id');

    // Shrink on scroll — only visually relevant for the floating (--overlay)
    // layout, but harmless to toggle regardless of which one this page has.
    const scrollRoot = document.getElementById('wrapwrap') || document.documentElement;
    scrollRoot.addEventListener('scroll', () => {
        header.classList.toggle('o_header_glass_scrolled', scrollRoot.scrollTop > 50);
    }, { passive: true });

    return header;
}

// ─────────────────────────────────────────────────────────────────────────────
// publicWidget — runs on every normal Odoo page that has a standard #top header.
// Skips on OmniGO/Omni360 pages (three_product.js calls initHeaderDropdowns
// directly there, after moving the icon bar into its own custom header).
// ─────────────────────────────────────────────────────────────────────────────
publicWidget.registry.headerDropdowns = publicWidget.Widget.extend({
    selector: 'header#top',

    start() {
        this._super(...arguments);

        if (document.querySelector('.o_omnigo_ch_header')) return;

        const header = buildSiteHeader(this.el);
        if (!header) return;

        const iconsUl =
            header.querySelector('ul.o_header_sales_one_right_col')
            || header.querySelector('.o_header_language_selector')?.closest('ul');
        if (!iconsUl || !iconsUl.children.length) return;

        initHeaderDropdowns(header, iconsUl);
    },
});
