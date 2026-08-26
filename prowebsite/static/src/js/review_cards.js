/** @odoo-module **/

// ─────────────────────────────────────────────────────────────────────────────
// Review "waterfall" cards — reveal-on-scroll
//
// Extracted from three_product.js (disabled in the manifest for the Odoo 19
// migration). Pure IntersectionObserver reveal with a staggered delay — no
// dependency on the 3D viewer or the store.
//
// Without this the cards keep whatever pre-reveal state the CSS gives them,
// since `is-visible` is never added. Styling lives in three_product.css
// (.o_review_waterfall_card), which stays enabled.
// ─────────────────────────────────────────────────────────────────────────────

import { whenReady } from "@odoo/owl";

whenReady(() => {
    const reviewCards = document.querySelectorAll(".o_review_waterfall_card");
    if (!reviewCards.length) return;

    const reviewObserver = new IntersectionObserver(
        (entries) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add("is-visible");
                    reviewObserver.unobserve(entry.target);
                }
            });
        },
        {
            threshold: 0.18,
            rootMargin: "0px 0px -8% 0px",
        }
    );

    reviewCards.forEach((card, index) => {
        card.style.transitionDelay = `${Math.min(index * 90, 450)}ms`;
        reviewObserver.observe(card);
    });
});
