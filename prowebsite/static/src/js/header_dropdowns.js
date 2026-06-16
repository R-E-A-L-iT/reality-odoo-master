/** @odoo-module **/
import { jsonrpc } from "@web/core/network/rpc_service";
import publicWidget from "@web/legacy/js/public/public_widget";

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
                <div class="o_hdd_col" data-cur-col>
                    <p class="o_hdd_col_label">Currency</p>
                    <div class="o_hdd_col_items" data-cur-items></div>
                </div>
            </div>
        </div>
    `;

    // Always append to body — position:fixed handles placement
    document.body.appendChild(bar);

    // ── Delegate language pill clicks to original Odoo anchors ────────────
    // Language is INDEPENDENT of currency here (the store's languages are
    // English / fr_CA / es_ES, which don't map to a currency). Copying the href
    // alone doesn't work for all languages: the default language often has
    // href="" on its .js_change_lang element, which our || '#' fallback turns
    // into a no-op anchor. Delegating to the original element ensures Odoo's own
    // click/routing logic runs instead.
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

    // ── Currency switcher (independent of language) ───────────────────────
    // Drives the store pricelist via the `pl_region` cookie, which the server
    // (proproduct/models/website.py) reads to resolve USD/CAD; when the cookie
    // is absent it falls back to geo-IP (the regional default). Clicking a
    // currency writes the cookie and reloads so prices re-render server-side.
    function setCurrencyRegion(region) {
        document.cookie = `pl_region=${region};path=/;max-age=31536000;SameSite=Lax`;
        window.location.reload();
    }

    const curItems = bar.querySelector('[data-cur-items]');
    const curCol   = bar.querySelector('[data-cur-col]');
    jsonrpc('/omnigo/get_pricelists', {}).then(list => {
        if (!Array.isArray(list) || list.length < 2 || !curItems) {
            // Nothing to switch between — hide the column.
            if (curCol) curCol.style.display = 'none';
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
    }).catch(() => {
        if (curCol) curCol.style.display = 'none';
    });

    // ── Keep bar pinned to the bottom edge of the header ──────────────────
    function updateBarTop() {
        bar.style.top = headerEl.offsetHeight + 'px';
    }
    updateBarTop();
    new ResizeObserver(updateBarTop).observe(headerEl);

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

    bar.addEventListener('mouseenter', () => clearTimeout(_hideTimer));
    bar.addEventListener('mouseleave', scheduleHide);
}

// ─────────────────────────────────────────────────────────────────────────────
// publicWidget — runs on every normal Odoo page that has a standard #top header.
// Skips on OmniGO pages (three_product.js calls initHeaderDropdowns directly
// after it has moved the icon bar into the custom header).
// ─────────────────────────────────────────────────────────────────────────────
publicWidget.registry.headerDropdowns = publicWidget.Widget.extend({
    selector: 'header#top',

    start() {
        this._super(...arguments);

        // The OmniGO page hides #top and builds its own header.
        // three_product.js calls initHeaderDropdowns() directly there.
        if (document.querySelector('.o_omnigo_ch_header')) return;

        // Find the icon <ul> — it is the last <ul> direct child of #o_main_nav
        const allUls = document.querySelectorAll('#o_main_nav > ul');
        const iconsUl = allUls.length > 0 ? allUls[allUls.length - 1] : null;
        if (!iconsUl || !iconsUl.children.length) return;

        initHeaderDropdowns(this.el, iconsUl);
    },
});
