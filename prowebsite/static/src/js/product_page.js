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

    // The single observer instance, so the injection routine can pause it while
    // it edits the DOM (otherwise its own edits re-trigger it — an infinite loop
    // that freezes the page).
    var observer = null;

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

        var badge = block.querySelector(".o_pp_price_currency");

        // Decide whether anything actually needs to change before touching the
        // DOM — writing unconditionally (even an identical textContent) is a
        // mutation that would wake the observer again.
        var needsText = !badge || badge.textContent !== code;
        var needsMove = !badge || badge.previousElementSibling !== price;
        if (!needsText && !needsMove) {
            return;
        }

        // Pause the observer around our own edits so they don't re-trigger it.
        if (observer) {
            observer.disconnect();
        }

        if (!badge) {
            badge = document.createElement("span");
            badge.className = "o_pp_price_currency";
        }
        if (needsText) {
            badge.textContent = code;
        }
        if (needsMove) {
            // insertAdjacentElement moves the node if it's already in the DOM.
            price.insertAdjacentElement("afterend", badge);
        }

        if (observer) {
            observer.observe(detail, { childList: true, subtree: true });
        }
    }

    function start() {
        injectCurrency();

        // The price-lock script swaps in .proproduct_locked_price after load and
        // re-renders on pricelist changes; re-run so the badge follows it.
        var detail = document.querySelector(".o_wsale_product_page #product_detail");
        if (detail) {
            observer = new MutationObserver(injectCurrency);
            observer.observe(detail, {
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
