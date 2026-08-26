/** @odoo-module **/

// ─────────────────────────────────────────────────────────────────────────────
// Promo popups — dismiss + notification stack (handles OmniGO AND RTC)
//
// Extracted from three_product.js, which is disabled in the manifest for the
// Odoo 19 migration (it also carries the 3D viewer and shop/product-page
// rewrites we don't want back yet). These popups are site-wide, not store
// features — the RTC pages are live and use .o_rtc_promo — so they were being
// styled by three_product.css while having no behaviour at all.
//
// Styling lives in three_product.css (.o_omnigo_promo / .o_rtc_promo /
// .o_promo_stack), which stays enabled.
// ─────────────────────────────────────────────────────────────────────────────

/* ─── Promo popup dismiss ──────────────────────────────────────────────────── */
// One delegated handler per close-button class. Finds the nearest ancestor
// promo card, lets its CSS transition collapse it (max-height/margin/opacity/
// transform, see .o_promo_stack .is-dismissed in three_product.css), then
// removes it from layout once that's done so the stack stays clean.
(function () {
    function dismissPromo(closeSelector, cardSelector) {
        document.addEventListener("click", function (e) {
            if (!e.target.closest(closeSelector)) return;
            var popup = e.target.closest(cardSelector);
            if (!popup) return;
            popup.classList.add("is-dismissed");
            // max-height is the longest-running of the transitioned properties
            // (0.4s, vs 0.22s for opacity/transform) — wait specifically for
            // it so display:none never cuts the collapse off mid-animation.
            function onEnd(ev) {
                if (ev.target !== popup || ev.propertyName !== "max-height") return;
                popup.removeEventListener("transitionend", onEnd);
                popup.style.display = "none";
            }
            popup.addEventListener("transitionend", onEnd);
        });
    }
    dismissPromo(".o_omnigo_promo_close", ".o_omnigo_promo");
    dismissPromo(".o_rtc_promo_close",    ".o_rtc_promo");
})();

/* ─── Notification stack — groups OmniGO + RTC popups ──────────────────────── */
// Runs immediately (no DOMContentLoaded wait needed — Odoo script injection
// happens after the DOM is already built). Finds any promo popups on the page,
// moves them into a single flex container so they stack and auto-collapse on dismiss.
(function () {
    var omnigo = document.querySelector(".o_omnigo_promo");
    var rtc    = document.querySelector(".o_rtc_promo");
    if (!omnigo && !rtc) return;

    var stack = document.createElement("div");
    stack.className = "o_promo_stack";

    // OmniGO on top, RTC below
    if (omnigo) { omnigo.parentNode.removeChild(omnigo); stack.appendChild(omnigo); }
    if (rtc)    { rtc.parentNode.removeChild(rtc);       stack.appendChild(rtc);    }

    document.body.appendChild(stack);
})();
