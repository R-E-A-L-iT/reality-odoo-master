/** @odoo-module **/
import { whenReady } from "@odoo/owl";

whenReady(() => {
    const page = document.querySelector(".o_mm_page");
    if (!page) return;

    // ── Image gallery — thumbnail → main image swap with auto-advance ────────
    page.querySelectorAll(".o_mm_gallery").forEach(gallery => {
        const mainImg = gallery.querySelector(".o_mm_main_img");
        const thumbs  = Array.from(gallery.querySelectorAll(".o_mm_thumb"));

        if (!mainImg || thumbs.length === 0) return;

        function setImage(src, activeThumb) {
            mainImg.classList.add("is-fading");
            setTimeout(() => {
                mainImg.src = src;
                mainImg.classList.remove("is-fading");
            }, 220);
            thumbs.forEach(t => t.classList.toggle("is-active", t === activeThumb));
        }

        let autoTimer = null;
        let currentIdx = 0;
        let userInteracted = false;

        function advance() {
            if (userInteracted) return;
            currentIdx = (currentIdx + 1) % thumbs.length;
            setImage(thumbs[currentIdx].dataset.src, thumbs[currentIdx]);
        }

        function startAuto() {
            clearInterval(autoTimer);
            autoTimer = setInterval(advance, 4000);
        }

        thumbs.forEach((thumb, i) => {
            thumb.addEventListener("click", () => {
                if (thumb.classList.contains("is-active")) return;
                userInteracted = true;
                currentIdx = i;
                clearInterval(autoTimer);
                setImage(thumb.dataset.src, thumb);
            });
        });

        // Pause auto-advance while gallery is out of view (save resources)
        const observer = new IntersectionObserver(([e]) => {
            if (e.isIntersecting && !userInteracted) {
                startAuto();
            } else {
                clearInterval(autoTimer);
            }
        }, { threshold: 0.3 });

        observer.observe(gallery);
    });

    // ── Specs section scrollspy — highlight active nav link ──────────────────
    const specNavLinks = Array.from(page.querySelectorAll(".o_mm_specs_nav_link"));
    const specGroups   = Array.from(page.querySelectorAll(".o_mm_spec_group[id]"));

    if (specNavLinks.length && specGroups.length) {
        const intersecting = new Set();

        const spyObserver = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    intersecting.add(entry.target);
                } else {
                    intersecting.delete(entry.target);
                }
            });

            let winner = null;
            let winnerTop = Infinity;
            intersecting.forEach(el => {
                const top = el.getBoundingClientRect().top;
                if (top < winnerTop) { winnerTop = top; winner = el; }
            });

            specNavLinks.forEach(link => {
                const id = link.getAttribute("href").slice(1);
                link.classList.toggle("is-active", winner !== null && winner.id === id);
            });
        }, { rootMargin: "-10% 0px -55% 0px", threshold: 0 });

        specGroups.forEach(g => spyObserver.observe(g));
    }
});
