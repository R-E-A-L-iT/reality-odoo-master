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

// #o_lg_lens_filter has to exist as real SVG markup somewhere in the page —
// CSS's `filter: url(#id)` can only reference a filter that's actually
// present in the DOM, there's no way to define one purely in a .css file.
// Injected once into <body>, hidden and zero-sized, the first time any
// .o_liquid_glass element initializes, so every instance across every page
// this class gets used on can rely on it being there without each one
// needing its own copy in its own template. Values (stdDeviation/scale)
// match the CodePen "liquid glass dock" demo this recipe is adapted from.
let lensFilterInjected = false;
function ensureLensFilter() {
    if (lensFilterInjected || document.getElementById("o_lg_lens_filter")) {
        lensFilterInjected = true;
        return;
    }
    lensFilterInjected = true;

    const svgNs = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNs, "svg");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("style", "position:absolute; width:0; height:0; overflow:hidden;");

    const filter = document.createElementNS(svgNs, "filter");
    filter.setAttribute("id", "o_lg_lens_filter");
    filter.setAttribute("x", "0%");
    filter.setAttribute("y", "0%");
    filter.setAttribute("width", "100%");
    filter.setAttribute("height", "100%");
    filter.setAttribute("filterUnits", "objectBoundingBox");

    const componentTransfer = document.createElementNS(svgNs, "feComponentTransfer");
    componentTransfer.setAttribute("in", "SourceAlpha");
    componentTransfer.setAttribute("result", "alpha");
    const funcA = document.createElementNS(svgNs, "feFuncA");
    funcA.setAttribute("type", "identity");
    componentTransfer.appendChild(funcA);

    const blur = document.createElementNS(svgNs, "feGaussianBlur");
    blur.setAttribute("in", "alpha");
    blur.setAttribute("stdDeviation", "50");
    blur.setAttribute("result", "blur");

    const displacement = document.createElementNS(svgNs, "feDisplacementMap");
    displacement.setAttribute("in", "SourceGraphic");
    displacement.setAttribute("in2", "blur");
    displacement.setAttribute("scale", "50");
    displacement.setAttribute("xChannelSelector", "A");
    displacement.setAttribute("yChannelSelector", "A");

    filter.appendChild(componentTransfer);
    filter.appendChild(blur);
    filter.appendChild(displacement);
    svg.appendChild(filter);
    document.body.appendChild(svg);
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

    // The glass background effect itself (unlike the tilt below) isn't
    // pointer/motion-dependent — needs to exist for every instance
    // regardless of the reduced-motion/coarse-pointer checks just below.
    ensureLensFilter();

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
