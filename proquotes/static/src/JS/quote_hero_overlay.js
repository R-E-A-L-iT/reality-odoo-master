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

        const notice = root.querySelector(".alert.css_editable_mode_hidden");
        if (notice) {
            notice.classList.add("o_liquid_glass");
            initLiquidGlassTilt(notice);
        }
    },
});
