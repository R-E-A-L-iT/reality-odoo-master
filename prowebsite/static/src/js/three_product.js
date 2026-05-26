/** @odoo-module **/

import { whenReady } from "@odoo/owl";

whenReady(async () => {
    const heroHost = document.getElementById("three-product-canvas");
    const bottomModelHost = document.getElementById("three-product-canvas-bottom-model");
    const scrollHost = document.getElementById("three-product-canvas-scroll");

    // ----------------------------
    // Custom Omni cursor
    // ----------------------------
    const omniPage = document.querySelector(".o_three_hero, .o_omnigo_buy_section, #omnigo-page-loader")?.closest("#wrap");

    let omniCursor = null;
    let omniCursorReady = false;

    function createOmniCursor() {
        if (!omniPage || omniCursorReady) {
            return;
        }

        omniCursorReady = true;

        document.body.classList.add("o_omnibase_custom_cursor_enabled");

        omniCursor = document.createElement("div");
        omniCursor.className = "o_omnibase_cursor";
        omniCursor.innerHTML = `
            <div class="o_omnibase_cursor_part o_omnibase_cursor_part_top"></div>
            <div class="o_omnibase_cursor_part o_omnibase_cursor_part_right"></div>
            <div class="o_omnibase_cursor_part o_omnibase_cursor_part_bottom"></div>
            <div class="o_omnibase_cursor_part o_omnibase_cursor_part_left"></div>
            <div class="o_omnibase_cursor_dot"></div>
        `;

        document.body.appendChild(omniCursor);

        // Batch cursor position to one rAF update per frame instead of every mousemove.
        let _cx = 0, _cy = 0, _cursorRaf = false;
        window.addEventListener("mousemove", (event) => {
            _cx = event.clientX; _cy = event.clientY;
            if (!_cursorRaf) {
                _cursorRaf = true;
                requestAnimationFrame(() => {
                    omniCursor.style.transform = `translate3d(${_cx}px, ${_cy}px, 0)`;
                    _cursorRaf = false;
                });
            }
        }, { passive: true });

        window.addEventListener("mousedown", () => {
            omniCursor.classList.add("is-clicking");
        });

        window.addEventListener("mouseup", () => {
            omniCursor.classList.remove("is-clicking");
        });

        window.addEventListener("mouseleave", () => {
            omniCursor.classList.add("is-hidden");
        });

        window.addEventListener("mouseenter", () => {
            omniCursor.classList.remove("is-hidden");
        });
    }

    createOmniCursor();

    // ----------------------------
    // Custom OmniGO page header
    // ----------------------------
    function createOmnigoHeader() {
        if (!omniPage) return;

        // Hide standard Odoo navbar and any submenu block
        const stdNav = document.getElementById("top");
        if (stdNav) stdNav.style.setProperty("display", "none", "important");
        const subMenu = document.querySelector(".s_submenu_block");
        if (subMenu) subMenu.style.setProperty("display", "none", "important");

        const header = document.createElement("header");
        header.className = "o_omnigo_ch_header";
        header.innerHTML = `
            <div class="o_omnigo_ch_inner">
                <div class="o_omnigo_ch_left">
                    <a href="/" class="o_omnigo_ch_logo_r" aria-label="R-E-A-L homepage">
                        <img src="https://cdn.r-e-a-l.it/images/header/r_circle.png" alt="R logo" class="o_omnigo_ch_r_img" />
                    </a>
                    <div class="o_omnigo_ch_divider"></div>
                    <a href="#" class="o_omnigo_ch_logo_omnigo" aria-label="OmniGO">
                        <img src="https://cdn.r-e-a-l.it/images/header/omnigo_draft.png" alt="OmniGO" class="o_omnigo_ch_omnigo_img" />
                    </a>
                </div>
                <nav class="o_omnigo_ch_nav" aria-label="OmniGO navigation">
                    <a href="#adapt" class="o_omnigo_ch_nav_link">Adapt</a>
                    <a href="#expand" class="o_omnigo_ch_nav_link">Expand</a>
                    <a href="#capture" class="o_omnigo_ch_nav_link">Capture</a>
                    <a href="#buy" class="o_omnigo_ch_buy_btn">Buy Now&thinsp;|&thinsp;$299</a>
                </nav>
                <button class="o_omnigo_ch_hamburger" aria-label="Open menu" aria-expanded="false">
                    <span></span><span></span><span></span>
                </button>
            </div>
            <div class="o_omnigo_ch_mobile_nav" aria-hidden="true">
                <a href="#adapt" class="o_omnigo_ch_mobile_link">Adapt</a>
                <a href="#expand" class="o_omnigo_ch_mobile_link">Expand</a>
                <a href="#capture" class="o_omnigo_ch_mobile_link">Capture</a>
                <a href="#buy" class="o_omnigo_ch_buy_btn o_omnigo_ch_mobile_buy">Buy Now&thinsp;|&thinsp;$299</a>
            </div>
        `;

        document.body.prepend(header);

        // Scroll shrink — Odoo scrolls #wrapwrap, not window
        const scrollRoot = document.getElementById("wrapwrap") || document.documentElement;
        scrollRoot.addEventListener("scroll", () => {
            header.classList.toggle("is-scrolled", scrollRoot.scrollTop > 50);
        }, { passive: true });

        // Hamburger toggle
        const burger = header.querySelector(".o_omnigo_ch_hamburger");
        const mobileNav = header.querySelector(".o_omnigo_ch_mobile_nav");
        burger.addEventListener("click", () => {
            const open = burger.getAttribute("aria-expanded") === "true";
            burger.setAttribute("aria-expanded", String(!open));
            burger.classList.toggle("is-open", !open);
            mobileNav.classList.toggle("is-open", !open);
            mobileNav.setAttribute("aria-hidden", String(open));
        });

        // Close mobile nav on link click; smooth-scroll #buy links
        mobileNav.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                burger.setAttribute("aria-expanded", "false");
                burger.classList.remove("is-open");
                mobileNav.classList.remove("is-open");
                mobileNav.setAttribute("aria-hidden", "true");
            });
        });

        // Smooth-scroll all header #buy links (desktop + mobile) instead of
        // hard-jumping, since Odoo scrolls #wrapwrap not window.
        header.querySelectorAll('a[href="#buy"]').forEach(btn => {
            btn.addEventListener("click", e => {
                const target = document.getElementById("buy");
                if (!target) return;
                e.preventDefault();
                target.scrollIntoView({ behavior: "smooth", block: "start" });
            });
        });

        // Nav link targets resolved lazily so the DOM is fully ready.
        // Adapt  → 1st video scroll section
        // Expand → 2nd video scroll section
        // Capture → Three.js scroll / feature-highlights section
        function scrollTo(el) {
            if (!el) return;
            el.scrollIntoView({ behavior: "smooth", block: "start" });
        }

        const navTargets = {
            "#adapt":   () => document.querySelectorAll(".o_omnigo_video_scroll_section")[0],
            "#expand":  () => document.querySelectorAll(".o_omnigo_video_scroll_section")[1],
            "#capture": () => document.querySelector(".o_three_scroll_section"),
        };

        header.querySelectorAll('a[href="#adapt"], a[href="#expand"], a[href="#capture"]').forEach(link => {
            link.addEventListener("click", e => {
                e.preventDefault();
                const getTarget = navTargets[link.getAttribute("href")];
                if (getTarget) scrollTo(getTarget());
            });
        });
    }

    createOmnigoHeader();

    // Wire the bouncing scroll arrow to smooth-scroll to the very next section.
    document.querySelectorAll(".o_omnigo_scroll_arrow").forEach(arrow => {
        arrow.addEventListener("click", e => {
            e.preventDefault();
            const heroSection = arrow.closest("section");
            const nextSection = heroSection?.nextElementSibling;
            if (nextSection) {
                nextSection.scrollIntoView({ behavior: "smooth", block: "start" });
            }
        });
    });

    const pageLoader = document.getElementById("omnigo-page-loader");

    // ── Loader logo colour-reveal setup ──────────────────────────────────────
    // The grey base image is already in the HTML (.o_omnigo_loader_logo).
    // We inject a full-colour clone on top and drive its clip-path left→right
    // as each asset loads, then auto-dismiss after 500 ms when all are done.
    let loaderLogoColor = null;

    if (pageLoader) {
        const loaderLogo = pageLoader.querySelector(".o_omnigo_loader_logo");
        if (loaderLogo) {
            // Wrap the existing logo so we can stack the colour clone on top.
            const wrap = document.createElement("div");
            wrap.className = "o_omnigo_loader_logo_wrap";
            loaderLogo.parentNode.insertBefore(wrap, loaderLogo);
            wrap.appendChild(loaderLogo);

            // Clone → full-colour overlay, starts fully clipped (no colour visible).
            loaderLogoColor = loaderLogo.cloneNode(true);
            loaderLogoColor.className = "o_omnigo_loader_logo_color";
            loaderLogoColor.removeAttribute("style");
            wrap.appendChild(loaderLogoColor);
        }
    }

    let pageAssetsReady = false;
    let userEnteredPage = false;

    let loadingTotal = 3; // adapter GLB, split model GLB, scroll video metadata
    let loadingDone = 0;

    function updateLoadingProgress(_label) {
        loadingDone += 1;

        const percent = Math.min((loadingDone / loadingTotal) * 100, 100);

        // Drive the colour reveal: clip from the right, shrinking toward 0.
        requestAnimationFrame(() => {
            if (loaderLogoColor) {
                loaderLogoColor.style.clipPath = `inset(0 ${100 - percent}% 0 0)`;
            }
        });

        if (loadingDone >= loadingTotal) {
            pageAssetsReady = true;

            // Snap fully revealed, then wait 500 ms and auto-dismiss.
            setTimeout(() => {
                if (loaderLogoColor) {
                    loaderLogoColor.style.clipPath = "inset(0 0% 0 0)";
                }
            }, 100);

            setTimeout(enterOmnigoPage, 1000);
        }
    }

    function enterOmnigoPage() {
        if (!pageAssetsReady || userEnteredPage) return;
        userEnteredPage = true;

        if (pageLoader) {
            pageLoader.classList.add("is-hidden");
        }

        // Reveal the custom header slightly into the loader fade-out.
        const ch = document.querySelector(".o_omnigo_ch_header");
        if (ch) {
            setTimeout(() => ch.classList.add("is-visible"), 400);
        }
    }

    if (!pageLoader) {
        // No loading screen on this page — enter immediately.
        pageAssetsReady = true;
        userEnteredPage = true;
        const ch = document.querySelector(".o_omnigo_ch_header");
        if (ch) ch.classList.add("is-visible");
    }

    const omnigoScrollVideo = document.getElementById("omnigo-scroll-video");

    // All video scroll sections — supports multiple on the same page.
    // Stamp each section with a data-video-index so CSS can alternate the
    // text-left / text-right split layout without a second query selector.
    const allVideoSections = [];
    document.querySelectorAll(".o_omnigo_video_scroll_section").forEach((sec, i) => {
        const vid = sec.querySelector(".o_omnigo_video_scroll_video");
        if (vid) {
            sec.dataset.videoIndex = i;
            allVideoSections.push({ sec, vid, seeking: false });
        }
    });

    if (!bottomModelHost || !scrollHost) {
        console.warn("[loader] early exit — missing host element(s), script will not run on this page");
        return;
    }

    let THREE;
    let GLTFLoader;
    let LoopPingPong;

    try {
        // Fetch Three.js core and GLTFLoader in parallel — saves one full CDN round-trip.
        const [threeModule, gltfModule] = await Promise.all([
            import("https://esm.sh/three@0.180.0"),
            import("https://esm.sh/three@0.180.0/examples/jsm/loaders/GLTFLoader.js"),
        ]);
        THREE = threeModule;
        ({ GLTFLoader } = gltfModule);
        LoopPingPong = THREE.LoopPingPong;
    } catch (err) {
        console.error("[loader] Failed to load Three.js:", err);
        return;
    }

    const adapterModelPath = "/prowebsite/static/src/models/BLK2GO_Adapter_V02B.glb";
    const splitModelPath   = "/prowebsite/static/src/models/BLK2GO_with_Scanner.glb";

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function easeInOutCubic(t) {
        return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
    }

    function lerp(a, b, t) {
        return a + (b - a) * t;
    }

    function createRenderer(targetHost, zIndex = "2") {
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
        });
        // renderer.outputColorSpace = THREE.SRGBColorSpace;
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        renderer.setSize(targetHost.clientWidth, targetHost.clientHeight);
        renderer.setClearColor(0x000000, 0);
        renderer.domElement.style.position = "absolute";
        renderer.domElement.style.inset = "0";
        renderer.domElement.style.zIndex = zIndex;
        renderer.domElement.style.background = "transparent";
        targetHost.appendChild(renderer.domElement);
        return renderer;
    }

    function addStandardLights(scene, variant = "dark") {
        const ambient = new THREE.AmbientLight(0xffffff, variant === "dark" ? 4.0 : 5.2);
        scene.add(ambient);

        const hemi = new THREE.HemisphereLight(
            0xffffff,
            variant === "dark" ? 0x444444 : 0xbbbbbb,
            variant === "dark" ? 3.2 : 4.2
        );
        hemi.position.set(0, 1, 0);
        scene.add(hemi);

        const dir1 = new THREE.DirectionalLight(0xffffff, variant === "dark" ? 4.8 : 6.4);
        dir1.position.set(5, 8, 6);
        scene.add(dir1);

        const dir2 = new THREE.DirectionalLight(0xffffff, variant === "dark" ? 2.8 : 4.4);
        dir2.position.set(-5, 4, 5);
        scene.add(dir2);

        const front = new THREE.DirectionalLight(0xffffff, variant === "dark" ? 6.4 : 8.0);
        front.position.set(0, 0, 8);
        front.target.position.set(0, 0, 0);
        scene.add(front);
        scene.add(front.target);
    }

    function addSoftProductLights(scene) {
        // Strong base visibility
        const ambient = new THREE.AmbientLight(0xffffff, 8.5);
        scene.add(ambient);

        const hemi = new THREE.HemisphereLight(0xffffff, 0x777777, 6.5);
        hemi.position.set(0, 1, 0);
        scene.add(hemi);

        // Large even front fill
        const frontCenter = new THREE.DirectionalLight(0xffffff, 5.5);
        frontCenter.position.set(0, 2, 7);
        scene.add(frontCenter);

        const frontLeft = new THREE.DirectionalLight(0xffffff, 4.2);
        frontLeft.position.set(-6, 3, 5);
        scene.add(frontLeft);

        const frontRight = new THREE.DirectionalLight(0xffffff, 4.2);
        frontRight.position.set(6, 3, 5);
        scene.add(frontRight);

        // Top fill so upper faces do not disappear
        const topLight = new THREE.DirectionalLight(0xffffff, 3.8);
        topLight.position.set(0, 8, 2);
        scene.add(topLight);

        // Lower fill so underside / red knob stays visible
        const lowerFill = new THREE.DirectionalLight(0xffffff, 3.0);
        lowerFill.position.set(0, -5, 4);
        scene.add(lowerFill);

        // Subtle brand-red rim/fill lights
        const redLeft = new THREE.DirectionalLight(0xff1a1a, 2.4);
        redLeft.position.set(-5, 1, 4);
        scene.add(redLeft);

        const redRight = new THREE.DirectionalLight(0xff2b2b, 2.0);
        redRight.position.set(5, 1, 3);
        scene.add(redRight);

        const redBackGlow = new THREE.PointLight(0xff0000, 3.2, 10);
        redBackGlow.position.set(0, 1.5, -3);
        scene.add(redBackGlow);
    }

    // ----------------------------
    // Shared adapter model cache (GLB)
    // ----------------------------
    let adapterPrototype = null;
    let adapterPromise = null;

    function prepareAdapterObject(obj) {
        obj.traverse((child) => {
            if (child.isMesh) {
                child.castShadow = false;
                child.receiveShadow = false;

                if (child.material) {
                    if (Array.isArray(child.material)) {
                        child.material = child.material.map((mat) => {
                            if (!mat) {
                                return mat;
                            }
                            const cloned = mat.clone();
                            cloned.side = THREE.DoubleSide;
                            cloned.needsUpdate = true;
                            return cloned;
                        });
                    } else {
                        child.material = child.material.clone();
                        child.material.side = THREE.DoubleSide;
                        child.material.needsUpdate = true;
                    }
                }
            }
        });

        const initialBox = new THREE.Box3().setFromObject(obj);
        const initialSize = initialBox.getSize(new THREE.Vector3());
        const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);

        if (maxAxis > 0) {
            const scale = 1.1 / maxAxis;
            obj.scale.setScalar(scale);
        }

        const box = new THREE.Box3().setFromObject(obj);
        const center = box.getCenter(new THREE.Vector3());
        obj.position.set(-center.x, -center.y, -center.z);

        return obj;
    }

    function loadAdapterPrototype() {
        if (adapterPromise) {
            return adapterPromise;
        }

        adapterPromise = new Promise((resolve, reject) => {
            const adapterLoader = new GLTFLoader();

            adapterLoader.load(
                adapterModelPath,
                (gltf) => {
                    adapterPrototype = prepareAdapterObject(gltf.scene);
                    updateLoadingProgress("adapter GLB");
                    resolve(adapterPrototype);
                },
                undefined,
                (err) => {
                    console.error("[loader] adapter GLB failed:", err);
                    reject(err);
                }
            );
        });

        return adapterPromise;
    }

    function createAdapterClone() {
        if (!adapterPrototype) {
            return null;
        }

        const clone = adapterPrototype.clone(true);

        clone.traverse((child) => {
            if (child.isMesh && child.material) {
                if (Array.isArray(child.material)) {
                    child.material = child.material.map((mat) => (mat ? mat.clone() : mat));
                } else {
                    child.material = child.material.clone();
                }
            }
        });

        return clone;
    }

    // ----------------------------
    // Bottom split-section left model
    // ----------------------------
    const bottomScene = new THREE.Scene();

    const bottomCamera = new THREE.PerspectiveCamera(
        40,
        bottomModelHost.clientWidth / bottomModelHost.clientHeight,
        0.1,
        1000
    );
    bottomCamera.position.set(0, 0, 5);

    const bottomRenderer = createRenderer(bottomModelHost, "1");
    addStandardLights(bottomScene, "light");

    let bottomWrapper = null;

    let bottomMixer = null;
    let bottomClock = new THREE.Clock();
    let bottomAction = null;
    const bottomAnimSpeed = 1.0;

    const bottomAutoRotateSpeed = 0.0018;
    const bottomResumeDelay = 3000;
    const bottomDragSensitivity = 0.02;

    let isBottomDragging = false;
    let bottomLastPointerX = 0;
    let bottomLastInteractionTime = 0;

    const bottomDefaultCameraZ = 5;
    const bottomMinCameraZ = 3.2;
    const bottomMaxCameraZ = 7.2;
    const bottomZoomStep = 0.35;

    bottomModelHost.style.cursor = "grab";
    bottomModelHost.style.touchAction = "none";

    function markBottomInteraction() {
        bottomLastInteractionTime = performance.now();
    }

    function bottomShouldAutoRotate(now) {
        return !isBottomDragging && (now - bottomLastInteractionTime >= bottomResumeDelay);
    }

    function onBottomPointerDown(event) {
        isBottomDragging = true;
        bottomLastPointerX = event.clientX;
        markBottomInteraction();
        bottomModelHost.style.cursor = "grabbing";

        if (bottomRenderer.domElement.setPointerCapture) {
            bottomRenderer.domElement.setPointerCapture(event.pointerId);
        }
    }

    function onBottomPointerMove(event) {
        if (!isBottomDragging || !bottomWrapper) {
            return;
        }

        const deltaX = event.clientX - bottomLastPointerX;
        bottomLastPointerX = event.clientX;

        bottomWrapper.rotation.y += deltaX * bottomDragSensitivity;
        markBottomInteraction();
    }

    function onBottomPointerUp(event) {
        isBottomDragging = false;
        markBottomInteraction();
        bottomModelHost.style.cursor = "grab";

        if (bottomRenderer.domElement.releasePointerCapture) {
            try {
                bottomRenderer.domElement.releasePointerCapture(event.pointerId);
            } catch (_err) {}
        }
    }

    function onBottomWheel(event) {
        event.preventDefault();

        const direction = Math.sign(event.deltaY);
        const nextZ = bottomCamera.position.z + direction * bottomZoomStep;

        bottomCamera.position.z = clamp(nextZ, bottomMinCameraZ, bottomMaxCameraZ);
        markBottomInteraction();
    }

    bottomRenderer.domElement.addEventListener("pointerdown", onBottomPointerDown);
    bottomRenderer.domElement.addEventListener("pointermove", onBottomPointerMove);
    bottomRenderer.domElement.addEventListener("pointerup", onBottomPointerUp);
    bottomRenderer.domElement.addEventListener("pointerleave", onBottomPointerUp);
    bottomRenderer.domElement.addEventListener("pointercancel", onBottomPointerUp);
    bottomRenderer.domElement.addEventListener("wheel", onBottomWheel, { passive: false });

    // ── Drag-to-rotate hint overlay ──────────────────────────────────────────
    // Wide curved double-headed arrow; hides while dragging, reappears after idle.
    const dragHint = document.createElement("div");
    dragHint.className = "o_omnigo_drag_hint";
    dragHint.innerHTML = `
        <svg width="88" height="40" viewBox="0 0 88 40" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <!-- Left filled arrowhead -->
            <polygon points="0,6 18,10 12,22" fill="currentColor"/>
            <!-- Wide smile arc connecting the two arrowheads -->
            <path d="M12 14 Q44 42 76 14"
                  stroke="currentColor" stroke-width="4" stroke-linecap="butt" fill="none"/>
            <!-- Right filled arrowhead -->
            <polygon points="88,6 70,10 76,22" fill="currentColor"/>
        </svg>
        <span class="o_omnigo_drag_hint__label">Drag to rotate</span>
    `;
    bottomModelHost.appendChild(dragHint);

    // Hide while user is interacting; reappear 3 s after they stop.
    let dragHintReappearTimer = null;

    function hideDragHint() {
        dragHint.classList.add("is-hidden");
        clearTimeout(dragHintReappearTimer);
        dragHintReappearTimer = setTimeout(() => {
            if (!isBottomDragging) dragHint.classList.remove("is-hidden");
        }, 3000);
    }

    bottomRenderer.domElement.addEventListener("pointermove", () => {
        if (isBottomDragging) hideDragHint();
    });
    bottomRenderer.domElement.addEventListener("wheel", hideDragHint, { passive: true });

    const gltfLoader = new GLTFLoader();

    // ----------------------------
    // Bottom split-section model (self-contained GLB — materials/textures embedded)
    // ----------------------------
    gltfLoader.load(
        splitModelPath,
        (gltf) => {
            const obj = gltf.scene;

            // Disable shadows (not needed for this panel).
            obj.traverse((child) => {
                if (!child.isMesh) return;
                child.castShadow = false;
                child.receiveShadow = false;
            });

            // Normalise size so the model fills the panel comfortably.
            const initialBox = new THREE.Box3().setFromObject(obj);
            const initialSize = initialBox.getSize(new THREE.Vector3());
            const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);
            if (maxAxis > 0) {
                obj.scale.setScalar(2.2 / maxAxis);
            }

            // Centre the model at the origin.
            const box = new THREE.Box3().setFromObject(obj);
            const center = box.getCenter(new THREE.Vector3());
            obj.position.set(-center.x, -center.y, -center.z);
            obj.rotation.x = 0;
            obj.rotation.z = 0;

            bottomWrapper = new THREE.Group();
            bottomWrapper.add(obj);
            bottomWrapper.position.set(0, 0, 0);
            bottomScene.add(bottomWrapper);

            bottomCamera.position.z = bottomDefaultCameraZ;
            markBottomInteraction();

            // Play embedded animation (ping-pong loop) if the GLB includes one.
            if (gltf.animations && gltf.animations.length > 0) {
                const clip = gltf.animations[0];
                bottomMixer = new THREE.AnimationMixer(obj);
                bottomAction = bottomMixer.clipAction(clip);
                bottomAction.setLoop(LoopPingPong, Infinity);
                bottomAction.clampWhenFinished = false;
                bottomAction.enabled = true;
                bottomAction.timeScale = bottomAnimSpeed;
                bottomAction.play();
            } else {
                console.warn("[loader] split model has no animations — showing static.");
            }

            updateLoadingProgress("split model GLB");
        },
        undefined,
        (error) => {
            console.error("[loader] split model failed:", error);
            updateLoadingProgress("split model GLB (failed)");
        }
    );

    // ----------------------------
    // Third scroll-scrubbed section
    // ----------------------------
    const scrollScene = new THREE.Scene();

    const scrollCamera = new THREE.PerspectiveCamera(
        45,
        scrollHost.clientWidth / scrollHost.clientHeight,
        0.1,
        1000
    );
    scrollCamera.position.set(0, 0, 5);

    const scrollRenderer = createRenderer(scrollHost, "1");
    addSoftProductLights(scrollScene);

    let scrollModel = null;
    let scrollWrapper = null;

    const scrollSection = scrollHost.closest(".o_three_scroll_section");
    let scrollHotspotLayer = null;
    let scrollDetailPanel = null;
    let scrollMobileLabels = null;

    // Cached hotspot element references — populated once in createScrollHotspots,
    // used every frame in updateScrollHotspots to avoid 8 querySelector calls/frame.
    let _elDetachAttachment = null, _elDetailBack = null, _elDetailHatch = null, _elDetailScrew = null;
    let _elMobileAttachment = null, _elMobileBack = null, _elMobileHatch = null, _elMobileScrew = null;

    // Cache the breakpoint result and update only when it actually changes.
    const _mqLarge = window.matchMedia("(min-width: 992px)");
    let _isLargeScreen = _mqLarge.matches;
    _mqLarge.addEventListener("change", e => { _isLargeScreen = e.matches; });
    function isLargeScreen() { return _isLargeScreen; }

    function createScrollHotspots() {
        if (!scrollHost) {
            return;
        }

        scrollHotspotLayer = document.createElement("div");
        scrollHotspotLayer.className = "o_three_scroll_hotspot_layer";

        scrollHotspotLayer.innerHTML = `
            <div class="o_three_feature_callout o_three_feature_callout_attachment">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">BLK2GO attachment interface</div>
            </div>

            <div class="o_three_feature_callout o_three_feature_callout_hatch">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">Latch lock button</div>
            </div>

            <div class="o_three_feature_callout o_three_feature_callout_screw">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">Multi-use screw attachment</div>
            </div>
        `;

        scrollHost.appendChild(scrollHotspotLayer);

        scrollDetailPanel = document.createElement("div");
        scrollDetailPanel.className = "o_three_scroll_detail_panel";
        scrollDetailPanel.innerHTML = `
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_attachment">
                <h3 class="o_three_scroll_feature_title">Universal Tripod Mount</h3>
                <p class="o_three_scroll_feature_body">The bottom face carries a standard 5/8″-11 thread that is common with survey tripods and poles, for uses in survey-centric applications.</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_back">
                <h3 class="o_three_scroll_feature_title">One-Touch Quick Release Button.</h3>
                <p class="o_three_scroll_feature_body">The red button is designed to be operated with a single press and hold for attaching and detaching from the standard Leica stub fitting to mount on survey poles.</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_hatch">
                <h3 class="o_three_scroll_feature_title">Quick-Release Latch.</h3>
                <p class="o_three_scroll_feature_body">The adapter can also be attached to a GAD52 (BLK360 adapter) for use on a monopod or tripod and have another option for quickly attaching and detaching of the BLK2GO.</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_screw">
                <h3 class="o_three_scroll_feature_title">BLK2GO Attachment Interface</h3>
                <p class="o_three_scroll_feature_body">The top face is precision-machined to grip the BLK2GO handle securely, distributing load evenly across the clamp surface to eliminate vibration and scanner wobble during movement.</p>
            </div>
        `;
        scrollHost.appendChild(scrollDetailPanel);

        scrollMobileLabels = document.createElement("div");
        scrollMobileLabels.className = "o_three_scroll_mobile_labels";
        scrollMobileLabels.innerHTML = `
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_attachment">BLK2GO Attachment Interface</div>
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_back">One-Touch Release Button</div>
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_hatch">Quick-Release Latch</div>
            <div class="o_three_scroll_mobile_label o_three_scroll_mobile_label_screw">Universal Tripod Mount</div>
        `;
        scrollHost.appendChild(scrollMobileLabels);

        // Cache refs so updateScrollHotspots never calls querySelector at runtime.
        _elDetachAttachment = scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_attachment");
        _elDetailBack       = scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_back");
        _elDetailHatch      = scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_hatch");
        _elDetailScrew      = scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_screw");
        _elMobileAttachment = scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_attachment");
        _elMobileBack       = scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_back");
        _elMobileHatch      = scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_hatch");
        _elMobileScrew      = scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_screw");
    }

    // ─── Scroll animation timing constants ───────────────────────────────────────
    // Each of the 4 features occupies one PHASE slot:
    //   [0 … TRANS)      — model animates to the new pose
    //   [TRANS … PHASE)  — model holds still; callout is visible   ← dwell
    // 4 × PHASE = 0.88; remaining 0.12 = return-to-rest transition.
    // All four dwell windows are exactly DWELL wide → consistent pause per feature.
    const SCROLL_TRANS = 0.08;                    // 8 % per transition
    const SCROLL_DWELL = 0.09;                    // 9 % per dwell (was 14 %)
    const SCROLL_PHASE = SCROLL_TRANS + SCROLL_DWELL; // 0.17 per feature

    function updateScrollHotspots() {
        if (!scrollHotspotLayer) return;
        const show = (el, on) => el && el.classList.toggle("is-visible", on);
        const p = scrollAnimProgress;
        const T = SCROLL_TRANS, PH = SCROLL_PHASE;
        const inA = p >= T          && p <= PH;
        const inB = p >= PH + T     && p <= PH * 2;
        const inH = p >= PH * 2 + T && p <= PH * 3;
        const inS = p >= PH * 3 + T && p <= PH * 4;
        show(_elDetachAttachment, inA); show(_elDetailBack, inB);
        show(_elDetailHatch,      inH); show(_elDetailScrew, inS);
        show(_elMobileAttachment, inA); show(_elMobileBack,  inB);
        show(_elMobileHatch,      inH); show(_elMobileScrew, inS);
    }

    let scrollAnimProgress = 0;

    function updateScrollSectionProgress() {
        if (!scrollSection) {
            return;
        }

        const rect = scrollSection.getBoundingClientRect();
        const viewportH = window.innerHeight || document.documentElement.clientHeight;

        const sectionActive = rect.top <= viewportH && rect.bottom >= 0;

        scrollHost.classList.toggle("is-active", sectionActive);

        if (!sectionActive) {
            return;
        }

        const scrollableDistance = rect.height - viewportH;

        if (scrollableDistance <= 0) {
            scrollAnimProgress = 0;
            return;
        }

        scrollAnimProgress = clamp(-rect.top / scrollableDistance, 0, 1);
    }

    function applyScrollSectionPose() {
        if (!scrollModel || !scrollWrapper) {
            return;
        }

        const t = scrollAnimProgress;

        // Resting pose — must match exactly at t=0 and t=1
        const baseY = -Math.PI / 12;
        const baseZ = Math.PI / 12;

        // Pitch targets for each revealed face
        const TOP_PITCH    = -Math.PI * 0.455; // ≈ -82°, top face tilted toward camera
        const SIDE_PITCH   = -Math.PI * 0.056; // ≈ -10°, nearly upright for side view
        const BOTTOM_PITCH =  Math.PI * 0.433; // ≈ +78°, bottom face tilted toward camera

        // Reuse the shared timing constants defined alongside updateScrollHotspots.
        // Layout (t = 0 … 1):
        //   Feature 1  [0.00 … 0.22]:  0.00–0.08 transition → top face;    0.08–0.22 dwell
        //   Feature 2  [0.22 … 0.44]:  0.22–0.30 transition → back face;   0.30–0.44 dwell
        //   Feature 3  [0.44 … 0.66]:  0.44–0.52 transition → side face;   0.52–0.66 dwell
        //   Feature 4  [0.66 … 0.88]:  0.66–0.74 transition → bottom face; 0.74–0.88 dwell
        //   Return     [0.88 … 1.00]:  return to resting pose
        const T  = SCROLL_TRANS; // 0.08
        const PH = SCROLL_PHASE; // 0.22
        const RETURN_DUR = 1 - PH * 4; // 0.12

        // Progress within each transition — clamp naturally holds at 1.0 during the dwell,
        // so no special dwell-phase branching is needed for the pose values.
        const p1 = easeInOutCubic(clamp(t / T, 0, 1));
        const p2 = easeInOutCubic(clamp((t - PH)     / T, 0, 1));
        const p3 = easeInOutCubic(clamp((t - PH * 2) / T, 0, 1));
        const p4 = easeInOutCubic(clamp((t - PH * 3) / T, 0, 1));
        const p5 = easeOutCubic(clamp((t - PH * 4) / RETURN_DUR, 0, 1));

        const desktop    = isLargeScreen();
        const scaleStart = desktop ? 1.50 : 1.30;
        const scalePeak  = desktop ? 1.85 : 1.55;

        // Scale: ramp up with first transition, hold at peak for all features, ramp down on return
        let scale;
        if (t < PH) {
            scale = lerp(scaleStart, scalePeak, p1);
        } else if (t < PH * 4) {
            scale = scalePeak;
        } else {
            scale = lerp(scalePeak, scaleStart, p5);
        }
        scrollWrapper.scale.setScalar(scale);

        // X offset: slide left on first transition (desktop only), hold, return
        let targetX;
        if (!desktop) {
            targetX = 0;
        } else if (t < PH) {
            targetX = lerp(0, -0.7, p1);
        } else if (t < PH * 4) {
            targetX = -0.7;
        } else {
            targetX = lerp(-0.7, 0, p5);
        }
        scrollWrapper.position.set(targetX, 0, 0);

        // Model pitch (X rotation)
        let modelX;
        if (t < PH) {
            modelX = lerp(0, TOP_PITCH, p1);              // tilt for top face
        } else if (t < PH * 2) {
            modelX = lerp(TOP_PITCH, 0, p2);              // come upright for back face
        } else if (t < PH * 3) {
            modelX = lerp(0, SIDE_PITCH, p3);             // slight tilt for side face
        } else if (t < PH * 4) {
            modelX = lerp(SIDE_PITCH, BOTTOM_PITCH, p4);  // tip forward for bottom face
        } else {
            modelX = lerp(BOTTOM_PITCH, 0, p5);           // return to rest
        }
        scrollModel.rotation.x = modelX;
        scrollModel.rotation.y = 0;
        scrollModel.rotation.z = 0;

        // Wrapper yaw (Y rotation)
        let wrapperY;
        if (t < PH) {
            wrapperY = baseY;
        } else if (t < PH * 2) {
            wrapperY = lerp(baseY, baseY + Math.PI, p2);
        } else if (t < PH * 3) {
            wrapperY = lerp(baseY + Math.PI, baseY + Math.PI * 0.5, p3);
        } else if (t < PH * 4) {
            wrapperY = lerp(baseY + Math.PI * 0.5, baseY, p4);
        } else {
            wrapperY = baseY;
        }
        scrollWrapper.rotation.y = wrapperY;

        // Wrapper roll (Z rotation): flatten slightly during feature phases
        let wrapperZ;
        if (t < PH) {
            wrapperZ = lerp(baseZ, baseZ * 0.4, p1);
        } else if (t < PH * 4) {
            wrapperZ = baseZ * 0.4;
        } else {
            wrapperZ = lerp(baseZ * 0.4, baseZ, p5);
        }
        scrollWrapper.rotation.z = wrapperZ;
        scrollWrapper.rotation.x = 0;

        updateScrollHotspots();
    }

    // ----------------------------
    // Shared adapter usage
    // ----------------------------
    await loadAdapterPrototype();

    // Scroll section adapter clone
    {
        const obj = createAdapterClone();

        scrollModel = obj;
        scrollWrapper = new THREE.Group();
        scrollWrapper.add(scrollModel);
        scrollWrapper.position.set(0, 0, 0);
        scrollScene.add(scrollWrapper);

        createScrollHotspots();
        applyScrollSectionPose();
    }

    // ----------------------------
    // Resize (debounced — resize events can fire dozens of times per drag)
    // ----------------------------
    let _resizeTimer = null;
    function onResize() {
        clearTimeout(_resizeTimer);
        _resizeTimer = setTimeout(() => {
            bottomCamera.aspect = bottomModelHost.clientWidth / bottomModelHost.clientHeight;
            bottomCamera.updateProjectionMatrix();
            bottomRenderer.setSize(bottomModelHost.clientWidth, bottomModelHost.clientHeight);
            scrollCamera.aspect = scrollHost.clientWidth / scrollHost.clientHeight;
            scrollCamera.updateProjectionMatrix();
            scrollRenderer.setSize(scrollHost.clientWidth, scrollHost.clientHeight);
        }, 150);
    }
    window.addEventListener("resize", onResize, { passive: true });

    // ----------------------------
    // Scroll dirty flag — avoids getBoundingClientRect() on every rAF frame.
    // Both updateScrollSectionProgress and updateOmnigoScrollVideo are now
    // driven by scroll events and only computed when the page actually scrolls.
    // ----------------------------
    const _scrollRoot = document.getElementById("wrapwrap") || document.documentElement;
    let _scrollDirty = true; // compute on first frame
    _scrollRoot.addEventListener("scroll", () => { _scrollDirty = true; }, { passive: true });

    // ----------------------------
    // Skip rendering when panels are off-screen (IntersectionObserver)
    // ----------------------------
    let _bottomInView = true; // assume visible until observer fires
    let _scrollSectionInView = false;
    new IntersectionObserver(([e]) => { _bottomInView = e.isIntersecting; }, { threshold: 0 })
        .observe(bottomModelHost);
    if (scrollSection) {
        new IntersectionObserver(([e]) => { _scrollSectionInView = e.isIntersecting; }, { threshold: 0 })
            .observe(scrollSection);
    }

    // ── Browser detection ────────────────────────────────────────────────────
    // Safari is identified by the absence of "Chrome"/"CriOS"/"FxiOS" in the UA
    // combined with the presence of "Safari". This catches desktop Safari and
    // iOS Safari (which uses the same WebKit engine and has the same video limits).
    const isSafari = /^((?!chrome|android|crios|fxios).)*safari/i.test(navigator.userAgent);

    // ── Safari path: seamless loop autoplay, no scroll scrubbing ────────────
    // The videos are already seamless loops, so native `loop` gives flicker-free
    // repeat without the seek-reliability issues that made ping-pong necessary.
    // Collapse the section to a normal height so the user scrolls past it naturally.
    if (isSafari && allVideoSections.length > 0) {
        allVideoSections.forEach(entry => {
            const { sec, vid } = entry;

            vid.muted = true;
            vid.loop  = true;
            vid.setAttribute("playsinline", "");
            vid.setAttribute("preload", "auto");

            // Collapse the tall scroll-scrub section to a normal viewport height.
            // Setting minHeight to "0" via inline style overrides the CSS 520vh rule;
            // leaving it as "" would remove the inline style and let 520vh reassert itself.
            sec.style.minHeight = "0";
            sec.style.height    = "100vh";
            const inner = sec.querySelector(".o_omnigo_video_scroll_inner");
            if (inner) inner.style.position = "relative";

            // Play when in view, pause when hidden.
            const observer = new IntersectionObserver(([obs]) => {
                if (obs.isIntersecting) {
                    vid.play().catch(() => {});
                } else {
                    vid.pause();
                }
            }, { threshold: 0.15 });

            observer.observe(sec);
        });
    }

    // ── Non-Safari path: scroll-scrubbed playback ─────────────────────────────
    if (!isSafari) {
        allVideoSections.forEach(entry => {
            const { vid } = entry;

            vid.muted = true;
            vid.setAttribute("playsinline", "");
            vid.setAttribute("preload", "auto");

            // Gate seeks on canplay — fires once the decoder has confirmed it can
            // decode the stream. Avoids readyState races that caused stalls.
            entry.canSeek = vid.readyState >= 2;
            entry.lastSeekAt = 0;

            if (!entry.canSeek) {
                vid.addEventListener("canplay", () => { entry.canSeek = true; }, { passive: true, once: true });
            }
        });
    }

    function updateOmnigoScrollVideo() {
        // No-op on Safari — ping-pong autoplay is handled by IntersectionObserver above.
        if (isSafari) return;

        const now = performance.now();
        allVideoSections.forEach(entry => {
            const { sec, vid } = entry;

            if (!entry.canSeek || !vid.duration) return;

            // Throttle to ~8 seeks/s.
            if (now - entry.lastSeekAt < 120) return;

            const rect = sec.getBoundingClientRect();
            const viewportH = window.innerHeight || document.documentElement.clientHeight;
            const totalScrollable = rect.height - viewportH;
            if (totalScrollable <= 0) return;

            const progress = clamp(-rect.top / totalScrollable, 0, 1);
            const targetTime = progress * vid.duration;

            if (Math.abs(vid.currentTime - targetTime) > 0.04) {
                entry.lastSeekAt = now;
                vid.currentTime = targetTime;
            }
        });
    }

    if (omnigoScrollVideo) {
        if (omnigoScrollVideo.readyState >= 1) {
            updateLoadingProgress("scroll video");
        } else {
            omnigoScrollVideo.addEventListener("loadedmetadata", () => {
                updateLoadingProgress("scroll video");
            }, { once: true });
        }
    } else {
        updateLoadingProgress("scroll video");
    }

    // ----------------------------
    // Animation loop
    // ----------------------------
    let _lastScrollProgress = -1;

    function animate(now) {
        requestAnimationFrame(animate);

        // Process scroll-driven updates only when the page actually scrolled.
        // This eliminates getBoundingClientRect() being called 60×/sec at rest.
        if (_scrollDirty) {
            _scrollDirty = false;
            updateScrollSectionProgress();
            updateOmnigoScrollVideo();
        }

        // Only run the expensive pose math when the progress value has changed.
        if (scrollAnimProgress !== _lastScrollProgress) {
            _lastScrollProgress = scrollAnimProgress;
            applyScrollSectionPose();
        }

        // Three.js model animation (always runs so the split model keeps animating)
        if (bottomMixer) {
            bottomMixer.update(bottomClock.getDelta());
        } else {
            bottomClock.getDelta(); // keep clock in sync
        }

        if (bottomWrapper && bottomShouldAutoRotate(now)) {
            bottomWrapper.rotation.y += bottomAutoRotateSpeed;
        }

        // Skip GPU render calls when the panel is off-screen — biggest frame-rate
        // saving when the user is far from either section.
        if (_bottomInView) {
            bottomRenderer.render(bottomScene, bottomCamera);
        }
        if (_scrollSectionInView) {
            scrollRenderer.render(scrollScene, scrollCamera);
        }
    }

    const reviewCards = document.querySelectorAll(".o_review_waterfall_card");

    if (reviewCards.length) {
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
    }

    requestAnimationFrame(animate);

    // ----------------------------
    // OmniGO buy section
    // ----------------------------
    function initOmnigoBuySection() {
        const buySection = document.querySelector(".o_omnigo_buy_section");
        if (!buySection) return;

        // NOTE: QWeb cannot place t-att-* on the outer <section> when the t-set blocks
        // that compute og_variant are children of that same element — the opening tag
        // is emitted before child directives run. The product ID therefore lives on
        // .o_omnigo_buy_inner, which is rendered *after* those t-set lines execute.
        const buyInner  = buySection.querySelector(".o_omnigo_buy_inner");
        if (!buyInner) return;

        const productId  = parseInt(buyInner.dataset.productId,  10);
        const templateId = parseInt(buyInner.dataset.templateId, 10) || null;
        if (!productId) {
            console.warn("[buy] data-product-id missing or zero on .o_omnigo_buy_inner");
            return;
        }


        const qtyInput = buySection.querySelector(".o_omnigo_buy_qty_input");
        const decBtn   = buySection.querySelector(".o_omnigo_buy_qty_dec");
        const incBtn   = buySection.querySelector(".o_omnigo_buy_qty_inc");
        const cartBtn  = buySection.querySelector(".o_omnigo_buy_cart_btn");
        const nowBtn   = buySection.querySelector(".o_omnigo_buy_now_btn");

        // Quantity stepper
        decBtn?.addEventListener("click", () => {
            qtyInput.value = Math.max(1, parseInt(qtyInput.value, 10) - 1);
        });
        incBtn?.addEventListener("click", () => {
            qtyInput.value = Math.min(99, parseInt(qtyInput.value, 10) + 1);
        });

        // Sync the session pricelist once at section init time (not on every click).
        // Our custom page displays the geo-IP-correct price via QWeb, but never writes
        // og_pl.id to request.session['website_sale_current_pl']. A stale session value
        // (e.g. from a previous Canadian visit) would make cart_update_json use the wrong
        // pricelist. This call clears the stale override and lets Odoo recalculate.
        const jq = window.$ || window.jQuery;
        const pricelistSyncPromise = new Promise(resolve => {
            jq.ajax({
                url: "/omnigo/sync_pricelist",
                method: "POST",
                contentType: "application/json",
                data: JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params: {} }),
                success(resp) {
                    const pl = resp?.result;
                    console.log("[buy] pricelist synced →", pl?.pricelist_name, `(${pl?.currency})`);

                    // Inject currency label next to price if not already present.
                    // Looks for .o_omnigo_buy_price_wrap > .o_omnigo_buy_price and
                    // appends a small <span class="o_omnigo_buy_currency">USD</span>.
                    if (pl?.currency) {
                        const priceEl = buySection.querySelector(".o_omnigo_buy_price");
                        if (priceEl && !priceEl.querySelector(".o_omnigo_buy_currency")) {
                            const badge = document.createElement("span");
                            badge.className = "o_omnigo_buy_currency";
                            badge.textContent = pl.currency;
                            priceEl.appendChild(badge);
                        }

                        // Update the header "Buy Now | $..." buttons with the
                        // live price shown on the page (same element, badge stripped).
                        const priceEl2 = buySection.querySelector(".o_omnigo_buy_price");
                        if (priceEl2) {
                            const clone = priceEl2.cloneNode(true);
                            clone.querySelector(".o_omnigo_buy_currency")?.remove();
                            // Typical QWeb output: "$ 2.00" — collapse whitespace
                            const rawText = clone.textContent.replace(/\s+/g, " ").trim();
                            const priceText = rawText.replace(/\.\d+/g, "");
                            const label = `Buy Now | ${priceText}`;
                            document.querySelectorAll(".o_omnigo_ch_buy_btn").forEach(btn => {
                                btn.textContent = label;
                            });
                        }
                    }

                    resolve(pl);
                },
                error(xhr) {
                    console.warn("[buy] pricelist sync failed (cart will use session default):", xhr.status);
                    resolve(null); // non-fatal — allow cart to proceed
                },
            });
        });

        // /shop/cart/update_json is type='json', csrf=False — the proper AJAX cart endpoint.
        // No CSRF token needed. Returns JSON-RPC { result: { cart_quantity, ... } }.
        async function callCartUpdate(qty) {
            // Ensure pricelist is synced before touching the cart.
            await pricelistSyncPromise;
            console.log("[buy] callCartUpdate →", { productId, templateId, qty });

            const params = { product_id: productId, add_qty: qty, display: false };
            if (templateId) params.product_template_id = templateId;

            return new Promise((resolve, reject) => {
                jq.ajax({
                    url: "/shop/cart/update_json",
                    method: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({ jsonrpc: "2.0", method: "call", id: 1, params }),
                    success(resp) {
                        if (resp?.error) {
                            const msg = resp.error.data?.message || resp.error.message || "Cart RPC error";
                            console.error("[buy] JSON-RPC error:", resp.error);
                            reject(new Error(msg));
                        } else {
                            resolve(resp?.result ?? {});
                        }
                    },
                    error(xhr) {
                        const preview = xhr.responseText?.slice(0, 300) || "";
                        console.error("[buy] cart update_json HTTP error:", xhr.status, preview);
                        reject(new Error(`Cart error (HTTP ${xhr.status})`));
                    },
                });
            });
        }

        // Sync Odoo's header cart badge (.my_cart_quantity) with the updated quantity.
        // JSON-RPC response shape: { result: { cart_quantity: N, ... } } — already unwrapped to result here.
        function syncCartBadge(result) {
            const newQty = result?.cart_quantity;
            if (newQty === undefined) {
                console.info("[buy] syncCartBadge: no cart_quantity in response", result);
                return;
            }
            document.querySelectorAll(".my_cart_quantity").forEach(el => {
                el.textContent = String(newQty);
            });
            // Show/hide the cart icon wrapper if Odoo hides it when empty
            document.querySelectorAll(".o_cart_button, a.o_extra_menu_items").forEach(el => {
                if (el.querySelector(".my_cart_quantity")) {
                    el.classList.toggle("d-none", newQty === 0);
                }
            });
        }

        function setBtnState(btn, state) {
            btn.dataset.state = state;
            btn.disabled = state === "loading";
        }

        cartBtn?.addEventListener("click", async () => {
            const qty = Math.max(1, parseInt(qtyInput.value, 10) || 1);
            setBtnState(cartBtn, "loading");
            try {
                const result = await callCartUpdate(qty);
                syncCartBadge(result);
                setBtnState(cartBtn, "added");
                setTimeout(() => setBtnState(cartBtn, ""), 2200);
            } catch (err) {
                console.error("[buy] add-to-cart failed:", err);
                setBtnState(cartBtn, "error");
                setTimeout(() => setBtnState(cartBtn, ""), 2200);
            }
        });

        // Inject "purchasing from outside US/CA?" note below the Buy Now button.
        if (nowBtn && !buySection.querySelector(".o_omnigo_buy_intl_note")) {
            const note = document.createElement("p");
            note.className = "o_omnigo_buy_intl_note";
            note.innerHTML = 'Are you purchasing from outside the U.S. or Canada? Contact us directly <a href="/contact">here</a> to place an order.';
            nowBtn.insertAdjacentElement("afterend", note);
        }

        nowBtn?.addEventListener("click", async () => {
            const qty = Math.max(1, parseInt(qtyInput.value, 10) || 1);
            setBtnState(nowBtn, "loading");
            try {
                const result = await callCartUpdate(qty);
                syncCartBadge(result);
                window.open("/shop/cart", "_blank");
                setBtnState(nowBtn, "");
            } catch (err) {
                console.error("[buy] buy-now failed:", err);
                setBtnState(nowBtn, "error");
                setTimeout(() => setBtnState(nowBtn, ""), 2200);
            }
        });
    }

    initOmnigoBuySection();

    // ----------------------------
    // FAQ accordion
    // ----------------------------
    // Single event listener on the list — no per-item listeners needed.
    const faqList = document.querySelector(".o_omnigo_faq_list");
    if (faqList) {
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
    }
});