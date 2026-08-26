/** @odoo-module **/

// ─────────────────────────────────────────────────────────────────────────────
// FAQ accordion
//
// Extracted from three_product.js (disabled in the manifest for the Odoo 19
// migration) so FAQ sections keep working on any page that renders the markup,
// independently of the 3D viewer and the store customizations.
//
// Styling lives in three_product.css (.o_omnigo_faq_*), which stays enabled.
// ─────────────────────────────────────────────────────────────────────────────

import { whenReady } from "@odoo/owl";

whenReady(() => {
    // Single event listener on the list — no per-item listeners needed.
    const faqList = document.querySelector(".o_omnigo_faq_list");
    if (!faqList) return;

    faqList.addEventListener("click", e => {
        const btn = e.target.closest(".o_omnigo_faq_q");
        if (!btn) return;
        const item = btn.closest(".o_omnigo_faq_item");
        if (!item) return;

        const isOpen = item.classList.contains("is-open");

        // Close any other open item first.
        faqList.querySelectorAll(".o_omnigo_faq_item.is-open").forEach(el => {
            el.classList.remove("is-open");
            el.querySelector(".o_omnigo_faq_q")?.setAttribute("aria-expanded", "false");
        });

        // Toggle the clicked item.
        if (!isOpen) {
            item.classList.add("is-open");
            btn.setAttribute("aria-expanded", "true");
        }
    });
});
