/* ════════════════════════════════════════════════════════════════════════════
   eCommerce product detail page — product_page.js
   Appends the active currency code (e.g. "USD" / "CAD") after the price, the
   same idea as the OmniGO page's .o_omnigo_buy_currency badge.

   The code is read from Odoo's server-rendered <span itemprop="priceCurrency">,
   which already reflects the active pricelist, so no extra request is needed.
   Pure presentation — no XML override.
   ════════════════════════════════════════════════════════════════════════════ */
(function () {
    "use strict";

    function injectCurrency() {
        var detail = document.querySelector(".o_wsale_product_page #product_detail");
        if (!detail) {
            return;
        }

        var block = detail.querySelector(".product_price");
        if (!block) {
            return;
        }

        var curEl = block.querySelector('[itemprop="priceCurrency"]');
        var code = curEl ? curEl.textContent.trim() : "";
        if (!code) {
            return;
        }

        // The visible price is the locked span (inserted by the price-lock
        // script) when present, otherwise Odoo's native .oe_price.
        var price = block.querySelector(".proproduct_locked_price")
            || block.querySelector(".oe_price");
        if (!price) {
            return;
        }

        // Idempotent: reuse the badge if it already exists (keeps it correct
        // across re-renders / pricelist switches).
        var badge = block.querySelector(".o_pp_price_currency");
        if (badge) {
            badge.textContent = code;
            // Keep it sitting right after the current visible price element.
            if (badge.previousElementSibling !== price) {
                price.insertAdjacentElement("afterend", badge);
            }
            return;
        }

        badge = document.createElement("span");
        badge.className = "o_pp_price_currency";
        badge.textContent = code;
        price.insertAdjacentElement("afterend", badge);
    }

    function start() {
        injectCurrency();

        // The price-lock script swaps in .proproduct_locked_price after load and
        // re-renders on pricelist changes; re-run so the badge follows it.
        var detail = document.querySelector(".o_wsale_product_page #product_detail");
        if (detail) {
            new MutationObserver(injectCurrency).observe(detail, {
                childList: true,
                subtree: true,
            });
        }

        // Safety re-runs mirroring the price-lock script's own timing.
        setTimeout(injectCurrency, 1500);
        setTimeout(injectCurrency, 4000);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", start);
    } else {
        start();
    }
})();
