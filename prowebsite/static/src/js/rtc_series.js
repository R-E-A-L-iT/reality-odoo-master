/** @odoo-module **/
import { whenReady } from "@odoo/owl";

whenReady(() => {
    const page = document.querySelector(".o_rtc_page");
    if (!page) return;

    // ── Tab switching ────────────────────────────────────────────────────────
    const tabs   = Array.from(page.querySelectorAll(".o_rtc_tab"));
    const panels = Array.from(page.querySelectorAll(".o_rtc_panel"));

    function activateTab(targetId) {
        tabs.forEach(t => t.classList.toggle("is-active", t.dataset.tab === targetId));
        panels.forEach(p => {
            const wasActive = p.classList.contains("is-active");
            const willActive = p.dataset.panel === targetId;
            if (!wasActive && willActive) {
                p.classList.add("is-active");
            } else if (wasActive && !willActive) {
                p.classList.remove("is-active");
            }
        });
    }

    tabs.forEach(tab => {
        tab.addEventListener("click", () => activateTab(tab.dataset.tab));
    });

    // ── Image gallery — per panel, shared thumbnail → main image swap ────────
    page.querySelectorAll(".o_rtc_gallery").forEach(gallery => {
        const mainImg = gallery.querySelector(".o_rtc_main_img");
        const thumbs  = Array.from(gallery.querySelectorAll(".o_rtc_thumb"));

        if (!mainImg || thumbs.length === 0) return;

        function setImage(src, activeThumb) {
            mainImg.classList.add("is-fading");
            setTimeout(() => {
                mainImg.src = src;
                mainImg.classList.remove("is-fading");
            }, 220);
            thumbs.forEach(t => t.classList.toggle("is-active", t === activeThumb));
        }

        thumbs.forEach(thumb => {
            thumb.addEventListener("click", () => {
                if (thumb.classList.contains("is-active")) return;
                setImage(thumb.dataset.src, thumb);
            });
        });

        // Auto-advance every 4 s when no user interaction
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
                userInteracted = true;
                currentIdx = i;
                clearInterval(autoTimer);
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
});
