/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { initLiquidGlassTilt } from "./liquid_glass";

// Keeps the quote-preview breadcrumb + "preview of the customer portal"
// notification pinned just below the site header instead of a hardcoded
// pixel guess — the header is position:fixed (so it reserves no space of its
// own) and its height varies (shrinks once .o_header_glass_scrolled kicks
// in), the same problem prowebsite's header_dropdowns.js already solved for
// its own dropdown bar via getBoundingClientRect() + ResizeObserver. This
// sets --quote-hero-header-h on <main>; the CSS in quote_preview.xml reads it
// for both elements' `top` offset.
//
// Also classes up the "preview of the customer portal" banner as
// .o_liquid_glass (see liquid_glass.css/js) — it can't carry that class from
// server-rendered markup since it comes from core Odoo's own template, not
// anything in this module, so it opts in here instead.
publicWidget.registry.quoteHeroOverlay = publicWidget.Widget.extend({
    selector: "main",

    async start() {
        await this._super(...arguments);

        if (!this.el.querySelector(".quote-hero-cover")) {
            return;
        }

        const root = this.el;
        const apply = (header) => {
            const update = () => {
                root.style.setProperty("--quote-hero-header-h", header.getBoundingClientRect().height + "px");
            };
            update();
            new ResizeObserver(update).observe(header);
        };

        const existing = document.querySelector(".o_site_header");
        if (existing) {
            apply(existing);
        } else {
            // prowebsite's header_dropdowns.js (buildSiteHeader) replaces the
            // native header with .o_site_header asynchronously relative to
            // this widget's own start() — there's no guaranteed load/
            // registration order between the two modules, so wait for it to
            // actually appear instead of assuming it's already there.
            const mo = new MutationObserver(() => {
                const header = document.querySelector(".o_site_header");
                if (header) {
                    mo.disconnect();
                    apply(header);
                }
            });
            mo.observe(document.body, { childList: true });
        }

        // ── Notification stack: preview banner → confirmed-order →
        //    order-shipped ──
        // Each one's --quote-notice-stack-offset is the summed height (+
        // gap) of every notice ahead of it in this order that's currently
        // visible — 0 if nothing ahead of it is showing, so it takes the
        // top spot on its own (the normal case for real customers, who
        // never see the preview banner at all). The CSS transition on
        // `top` (quotePreview.css) is what makes a notice glide smoothly
        // into a freed-up spot when something ahead of it is dismissed,
        // instead of jump-cutting there.
        //
        // getNotices() re-queries fresh every single call rather than
        // closing over a list captured once — the preview banner
        // specifically isn't guaranteed to exist yet the first time this
        // runs (it's Odoo's own editor-preview-mode banner, inserted by a
        // separate, unrelated script with no guaranteed ordering relative
        // to this one), so a stale snapshot from before it existed would
        // never include it even after it shows up. One single observer set
        // up once (not one created fresh per call) watching only
        // childList — element *removal* (what Bootstrap's dismiss actually
        // does once its own fade-out finishes) is a childList change on
        // the parent, so this alone catches every notice both arriving
        // and being dismissed, without needing to watch attributes too.
        // That mattered: watching style/class attributes as well
        // previously caught this same code's own `style.setProperty` calls
        // below, retriggering itself in a feedback loop — combined with
        // this observer being (re)created on every call instead of once,
        // multiple overlapping copies ended up fighting over the same
        // elements, which is what made the stack settle into the right
        // spot for a moment and then visibly snap back to overlapping.
        const getNotices = () =>
            [
                root.querySelector(".alert.css_editable_mode_hidden"),
                root.querySelector(".quote-confirmed-notice"),
                root.querySelector(".quote-shipped-notice"),
            ].filter(Boolean);

        if (getNotices().length) {
            const classified = new WeakSet();
            const classify = () => {
                getNotices().forEach((el, i) => {
                    if (classified.has(el)) {
                        return;
                    }
                    classified.add(el);
                    el.classList.add("o_liquid_glass");
                    initLiquidGlassTilt(el);

                    // "Back to edit mode" is core Odoo markup (not ours to
                    // add a class to directly) but needs the same button
                    // styling as the tracking-number link below — see
                    // .quote-notice-link in quotePreview.css.
                    const link = el.querySelector(".alert-link");
                    if (link) {
                        link.classList.add("quote-notice-link");
                    }

                    // First notice in the stack plays its entrance after
                    // the usual 3s pause; each one after that follows
                    // 0.5s behind the one before it, rather than every
                    // notice independently waiting the same flat 3s (which
                    // made a full stack take 3 separate 3-second delays,
                    // one per notice, to finish appearing).
                    el.style.setProperty("--quote-notice-delay", (3 + i * 0.5) + "s");
                });
            };

            const lastOffsets = new WeakMap();
            const updateStack = () => {
                let offset = 0;
                for (const el of getNotices()) {
                    const value = offset + "px";
                    if (lastOffsets.get(el) !== value) {
                        lastOffsets.set(el, value);
                        el.style.setProperty("--quote-notice-stack-offset", value);
                    }
                    // A detached or display:none element reports an all-
                    // zero rect — offsetParent is unreliable for this
                    // (always null for position:fixed regardless of actual
                    // visibility), which is what this used to check.
                    const rect = el.getBoundingClientRect();
                    if (rect.height > 0) {
                        offset += rect.height + 14;
                    }
                }
            };

            classify();
            updateStack();

            // Bootstrap's own event, fired once its dismiss animation
            // finishes removing the alert — listened for on document since
            // it bubbles, catching every notice regardless of whether it
            // existed yet when this widget started.
            document.addEventListener("closed.bs.alert", () => {
                classify();
                updateStack();
            });
            new MutationObserver(() => {
                classify();
                updateStack();
            }).observe(document.body, { childList: true, subtree: true });
        }

        // Fade the hero title/address (and the quicknav) out as the page
        // scrolls — the hero itself is position:fixed (see quote_preview.xml)
        // so it never moves on its own; --quote-hero-text-fade drives the
        // CSS opacity instead. Fully faded by 0.7 viewport heights of
        // scroll, well before the Quotation card's top would otherwise
        // start fighting the quicknav for clicks at the bottom of the
        // screen. --quote-hero-nav-pe switches the quicknav's pointer-events
        // off once it's essentially invisible, so an unclickable-by-eye nav
        // doesn't sit there intercepting clicks meant for the card beneath
        // it once scrolled past.
        //
        // The theme scrolls #wrapwrap internally rather than the window
        // (html/body themselves never scroll) — same reason
        // header_dropdowns.js listens on #wrapwrap instead of window for its
        // own scroll-driven effects. window.scrollY would just stay 0 here.
        if (root.querySelector(".quote-hero-text, .quote-hero-quicknav")) {
            const scrollEl = document.getElementById("wrapwrap") || window;
            const getScrollTop = () => scrollEl === window ? window.scrollY : scrollEl.scrollTop;

            let raf = null;
            const updateFade = () => {
                raf = null;
                const fadeDistance = window.innerHeight * 0.7;
                const fade = Math.max(0, 1 - getScrollTop() / fadeDistance);
                root.style.setProperty("--quote-hero-text-fade", fade.toFixed(3));
                root.style.setProperty("--quote-hero-nav-pe", fade < 0.05 ? "none" : "auto");
            };
            updateFade();
            scrollEl.addEventListener("scroll", () => {
                if (raf === null) {
                    raf = requestAnimationFrame(updateFade);
                }
            }, { passive: true });
        }
    },
});
