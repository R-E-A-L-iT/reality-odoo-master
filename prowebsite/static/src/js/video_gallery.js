/** @odoo-module **/

// ─────────────────────────────────────────────────────────────────────────────
// Video gallery carousel — infinite loop with peek
//
// Extracted verbatim from three_product.js's initVideoGallery(). That file is
// currently disabled in the manifest for the Odoo 19 migration (it also carries
// the shop/product-page rewrites we don't want back yet), which left this
// section styled by three_product.css but with no behaviour at all — the arrows
// did nothing and the counter stayed at its template placeholder.
//
// Keeping the gallery in its own asset means it works on any page that renders
// the .o_omnigo_vgallery_section markup, independently of the 3D viewer and of
// whatever happens to the rest of three_product.js during the migration.
//
// The markup lives in the website page content (DB), not in a module template.
// The CSS lives in three_product.css (.o_omnigo_vgallery_*).
// ─────────────────────────────────────────────────────────────────────────────

import { whenReady } from "@odoo/owl";

whenReady(() => {
    const section = document.querySelector(".o_omnigo_vgallery_section");
    if (!section) return; // no gallery on this page

    // ── i18n ─────────────────────────────────────────────────────────────────
    // Only the keys this component actually uses. Mirrors the _t() contract in
    // three_product.js: function-valued entries receive the extra args.
    const pageLang = (document.documentElement.lang || "en_US").replace("-", "_");

    const _i18n = {
        fr_CA: { goToVideo: (n) => `Aller à la vidéo ${n}` },
        es_ES: { goToVideo: (n) => `Ir al video ${n}` },
    };

    function _t(key, fallback, ...args) {
        const dict = _i18n[pageLang];
        const val = dict ? dict[key] : undefined;
        if (val === undefined) {
            return typeof fallback === "function" ? fallback(...args) : fallback;
        }
        return typeof val === "function" ? val(...args) : val;
    }

    const track      = section.querySelector(".o_omnigo_vgallery_track");
    const origSlides = Array.from(section.querySelectorAll(".o_omnigo_vgallery_slide"));
    const prevBtn    = section.querySelector(".o_omnigo_vgallery_arrow.is-prev");
    const nextBtn    = section.querySelector(".o_omnigo_vgallery_arrow.is-next");
    const dotsWrap   = section.querySelector(".o_omnigo_vgallery_dots");
    const counter    = section.querySelector(".o_omnigo_vgallery_counter");

    if (!track || origSlides.length === 0) return;

    const total = origSlides.length;

    // Must match the CSS values:
    //   .o_omnigo_vgallery_slide  { flex: 0 0 calc(100% - 220px) }  → PEEK = 110
    //   .o_omnigo_vgallery_track  { gap: 16px }                      → GAP  = 16
    const PEEK = 110;
    const GAP  = 16;

    // ── Clone first / last slides for seamless infinite loop ─────────────────
    const firstClone = origSlides[0].cloneNode(true);
    const lastClone  = origSlides[total - 1].cloneNode(true);
    firstClone.setAttribute("aria-hidden", "true");
    lastClone.setAttribute("aria-hidden",  "true");
    track.appendChild(firstClone);
    track.prepend(lastClone);
    // DOM layout: [lastClone(0), slide0(1) … slideN-1(N), firstClone(N+1)]

    const allSlides = Array.from(track.children);

    let domIdx    = 1;   // DOM index of the currently visible slide
    let realIdx   = 0;   // 0-based index into the original slides
    let animating = false;

    // ── Layout helpers ───────────────────────────────────────────────────────
    // CSS owns the slide width and the gap. JS just reads the rendered width.
    function slideW() {
        return allSlides[1]?.offsetWidth || (track.parentElement.offsetWidth - 2 * PEEK);
    }

    function offsetFor(d) {
        // translateX that places the left edge of slide d at x = PEEK
        return PEEK - d * (slideW() + GAP);
    }

    function applyTranslate(px, animated) {
        track.style.transition = animated
            ? "transform 0.42s cubic-bezier(0.4, 0, 0.2, 1)"
            : "none";
        track.style.transform = `translateX(${px}px)`;
    }

    function markActive() {
        allSlides.forEach((s, i) => s.classList.toggle("is-active", i === domIdx));
    }

    // ── Dots ─────────────────────────────────────────────────────────────────
    const dots = origSlides.map((_, i) => {
        const dot = document.createElement("button");
        dot.className = "o_omnigo_vgallery_dot";
        dot.setAttribute("aria-label", _t("goToVideo", (n) => `Go to video ${n}`, i + 1));
        dot.addEventListener("click", () => {
            if (!animating) goTo(i + 1, i);
        });
        dotsWrap?.appendChild(dot);
        return dot;
    });

    function updateUI() {
        dots.forEach((d, i) => d.classList.toggle("is-active", i === realIdx));
        if (counter) counter.textContent = `${realIdx + 1} / ${total}`;
        markActive();
    }

    // ── Pause Vimeo without reloading (postMessage API) ──────────────────────
    function pauseVimeo(slideEl) {
        const iframe = slideEl?.querySelector(".o_omnigo_vgallery_iframe");
        if (!iframe?.contentWindow) return;
        try {
            iframe.contentWindow.postMessage(
                JSON.stringify({ method: "pause" }),
                "https://player.vimeo.com"
            );
        } catch (_) {}
    }

    // ── Navigation ───────────────────────────────────────────────────────────
    function goTo(targetDom, targetReal) {
        if (animating) return;
        pauseVimeo(allSlides[domIdx]);
        animating = true;
        domIdx  = targetDom;
        realIdx = targetReal;
        applyTranslate(offsetFor(domIdx), true);
        updateUI();
    }

    function next() {
        const nd = domIdx + 1;
        const nr = nd <= total ? nd - 1 : 0;
        goTo(nd, nr);
    }

    function prev() {
        const nd = domIdx - 1;
        const nr = nd >= 1 ? nd - 1 : total - 1;
        goTo(nd, nr);
    }

    // ── Infinite-loop snap (silently jump clone → real slide) ────────────────
    track.addEventListener("transitionend", e => {
        if (e.propertyName !== "transform") return;
        animating = false;

        if (domIdx === 0) {
            // Arrived at lastClone → snap to real last slide
            domIdx  = total;
            realIdx = total - 1;
            applyTranslate(offsetFor(domIdx), false);
            markActive();
        } else if (domIdx === total + 1) {
            // Arrived at firstClone → snap to real first slide
            domIdx  = 1;
            realIdx = 0;
            applyTranslate(offsetFor(domIdx), false);
            markActive();
        }
    });

    // ── Event wiring ─────────────────────────────────────────────────────────
    prevBtn?.addEventListener("click", prev);
    nextBtn?.addEventListener("click", next);

    section.addEventListener("keydown", e => {
        if (e.key === "ArrowLeft")  { e.preventDefault(); prev(); }
        if (e.key === "ArrowRight") { e.preventDefault(); next(); }
    });

    let _tx = 0;
    const trackWrap = section.querySelector(".o_omnigo_vgallery_track_wrap");
    trackWrap?.addEventListener("touchstart", e => { _tx = e.touches[0].clientX; }, { passive: true });
    trackWrap?.addEventListener("touchend", e => {
        const delta = e.changedTouches[0].clientX - _tx;
        if (Math.abs(delta) > 44) { delta < 0 ? next() : prev(); }
    }, { passive: true });

    // Reposition on window resize (CSS re-computes slide width automatically;
    // we just need to recalculate the translateX offset to match).
    let _rt = null;
    window.addEventListener("resize", () => {
        clearTimeout(_rt);
        _rt = setTimeout(doLayout, 120);
    }, { passive: true });

    // ── Single-video mode — no carousel needed ───────────────────────────────
    if (total === 1) {
        prevBtn?.setAttribute("data-hidden", "true");
        nextBtn?.setAttribute("data-hidden", "true");
        if (dotsWrap) dotsWrap.style.display = "none";
        if (counter)  counter.style.display  = "none";
    }

    // ── Init ─────────────────────────────────────────────────────────────────
    // CSS controls slide width and aspect ratio, so all we need to do is read
    // the rendered slide width and apply the correct translateX. ResizeObserver
    // on the stage makes this fire after the browser has done a layout pass and
    // allSlides[1].offsetWidth is non-zero.
    function doLayout() {
        applyTranslate(offsetFor(domIdx), false);
    }

    const stage = section.querySelector(".o_omnigo_vgallery_stage");
    const ro = new ResizeObserver(entries => {
        for (const entry of entries) {
            if (entry.contentRect.width > 0) {
                doLayout();
                // Enable CSS transition only after first real paint so the
                // initial snap doesn't animate in from position 0.
                requestAnimationFrame(() => {
                    track.style.transition = "transform 0.42s cubic-bezier(0.4, 0, 0.2, 1)";
                });
                ro.disconnect();
            }
        }
    });
    ro.observe(stage || track.parentElement);

    // Try synchronously too — works when the page is served from cache and
    // offsetWidth is already valid at script-execution time.
    doLayout();

    updateUI();
});
