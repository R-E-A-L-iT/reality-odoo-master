/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

// Pointer-reactive tilt for .o_liquid_glass cards (see liquid_glass.css) — a
// small, constant "give" toward wherever the cursor is on the page, like the
// card stays put but is a little magnetic, rather than a hover-only 3D tilt
// that snaps back the instant the pointer leaves the element's own box.
// Tracks mousemove on the whole window (not just the element) so the effect
// fades in/out smoothly as the cursor approaches/leaves instead of switching
// on and off at the element's edge.
const MAX_DEG = 5;
const MAX_TRANSLATE = 6;
const INFLUENCE_RADIUS = 480;

const prefersReducedMotion = () =>
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;
const isFinePointer = () =>
    window.matchMedia("(hover: hover) and (pointer: fine)").matches;

function resetTilt(el) {
    el.style.setProperty("--o_lg_rx", "0deg");
    el.style.setProperty("--o_lg_ry", "0deg");
    el.style.setProperty("--o_lg_tx", "0px");
    el.style.setProperty("--o_lg_ty", "0px");
    el.style.setProperty("--o_lg_glint_x", "30%");
    el.style.setProperty("--o_lg_glint_y", "-10%");
}

// Exported (not just registered as a widget) because some .o_liquid_glass
// instances get their class added dynamically after publicWidget's own
// selector-based scan already ran (e.g. the quote-preview banner in
// quote_hero_overlay.js, which classes up a core-Odoo element it can't mark
// with the class from server-rendered markup) — those need to opt in
// directly instead of relying on auto-attachment.
export function initLiquidGlassTilt(el) {
    if (!el || el.__liquidGlassTiltInit) {
        return;
    }
    el.__liquidGlassTiltInit = true;

    if (prefersReducedMotion() || !isFinePointer()) {
        return;
    }

    let raf = null;
    const onMove = (ev) => {
        if (raf) {
            return;
        }
        raf = requestAnimationFrame(() => {
            raf = null;
            const rect = el.getBoundingClientRect();
            const cx = rect.left + rect.width / 2;
            const cy = rect.top + rect.height / 2;
            const dx = ev.clientX - cx;
            const dy = ev.clientY - cy;
            const dist = Math.hypot(dx, dy);
            const influence = Math.max(0, 1 - dist / INFLUENCE_RADIUS);

            const ry = (dx / INFLUENCE_RADIUS) * MAX_DEG * influence;
            const rx = -(dy / INFLUENCE_RADIUS) * MAX_DEG * influence;
            const tx = (dx / INFLUENCE_RADIUS) * MAX_TRANSLATE * influence;
            const ty = (dy / INFLUENCE_RADIUS) * MAX_TRANSLATE * influence;

            el.style.setProperty("--o_lg_rx", rx.toFixed(2) + "deg");
            el.style.setProperty("--o_lg_ry", ry.toFixed(2) + "deg");
            el.style.setProperty("--o_lg_tx", tx.toFixed(2) + "px");
            el.style.setProperty("--o_lg_ty", ty.toFixed(2) + "px");
            el.style.setProperty("--o_lg_glint_x", (30 - ry * 3).toFixed(1) + "%");
            el.style.setProperty("--o_lg_glint_y", (-10 + rx * 3).toFixed(1) + "%");
        });
    };

    // Pointer leaving the browser window entirely (relatedTarget null on the
    // document) stops mousemove events from firing at all — without this the
    // card would freeze mid-tilt instead of settling back to resting.
    const onDocumentMouseOut = (ev) => {
        if (!ev.relatedTarget) {
            resetTilt(el);
        }
    };

    window.addEventListener("mousemove", onMove, { passive: true });
    document.addEventListener("mouseout", onDocumentMouseOut, { passive: true });
}

publicWidget.registry.liquidGlassTilt = publicWidget.Widget.extend({
    selector: ".o_liquid_glass",

    start() {
        this._super(...arguments);
        initLiquidGlassTilt(this.el);
    },
});
