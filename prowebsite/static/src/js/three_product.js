/** @odoo-module **/

import { whenReady } from "@odoo/owl";

whenReady(async () => {
    console.log("[loader] whenReady fired");

    const heroHost = document.getElementById("three-product-canvas");
    const bottomModelHost = document.getElementById("three-product-canvas-bottom-model");
    const scrollHost = document.getElementById("three-product-canvas-scroll");

    console.log("[loader] host elements:", {
        heroHost: !!heroHost,
        bottomModelHost: !!bottomModelHost,
        scrollHost: !!scrollHost,
    });

    // ----------------------------
    // Custom Omni cursor
    // ----------------------------
    const omniPage = document.querySelector(".o_three_hero")?.closest("#wrap");

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

        window.addEventListener("mousemove", (event) => {
            omniCursor.style.transform = `translate3d(${event.clientX}px, ${event.clientY}px, 0)`;
        });

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

        // Close mobile nav on link click
        mobileNav.querySelectorAll("a").forEach(link => {
            link.addEventListener("click", () => {
                burger.setAttribute("aria-expanded", "false");
                burger.classList.remove("is-open");
                mobileNav.classList.remove("is-open");
                mobileNav.setAttribute("aria-hidden", "true");
            });
        });
    }

    createOmnigoHeader();

    const pageLoader = document.getElementById("omnigo-page-loader");
    const loaderFill = pageLoader ? pageLoader.querySelector(".o_omnigo_loader_bar_fill") : null;
    const loaderEnter = pageLoader ? pageLoader.querySelector(".o_omnigo_loader_enter") : null;

    let pageAssetsReady = false;
    let userEnteredPage = false;

    let loadingTotal = 3; // adapter GLB, animated GLTF, scroll video metadata
    let loadingDone = 0;

    function updateLoadingProgress(label) {
        loadingDone += 1;
        console.log(`[loader] step ${loadingDone}/${loadingTotal} — ${label}`);

        const rawPercent = Math.min((loadingDone / loadingTotal) * 100, 100);

        // Slight delay lets each step animate instead of snapping visually
        requestAnimationFrame(() => {
            if (loaderFill) {
                loaderFill.style.width = `${rawPercent}%`;
            }
        });

        if (loadingDone >= loadingTotal) {
            pageAssetsReady = true;

            if (loaderFill) {
                setTimeout(() => {
                    loaderFill.style.width = "100%";
                }, 150);
            }

            if (loaderEnter) {
                setTimeout(() => {
                    loaderEnter.classList.add("is-visible");
                }, 900);
            }
        }
    }

    function enterOmnigoPage() {
        if (!pageAssetsReady) {
            return;
        }

        userEnteredPage = true;

        if (pageLoader) {
            pageLoader.classList.add("is-hidden");
        }

        // Reveal the custom header after the loading screen fades out
        const ch = document.querySelector(".o_omnigo_ch_header");
        if (ch) {
            setTimeout(() => ch.classList.add("is-visible"), 400);
        }

        // Start hero drop animation only after Enter
        if (heroWrapper) {
            heroWrapper.position.y = 3.5;
            dropAnimationStart = performance.now();
        }
    }

    if (loaderEnter) {
        loaderEnter.addEventListener("click", enterOmnigoPage);
    }

    const omnigoScrollVideo = document.getElementById("omnigo-scroll-video");
    const omnigoVideoSection = omnigoScrollVideo
        ? omnigoScrollVideo.closest(".o_omnigo_video_scroll_section")
        : null;

    // All video scroll sections — supports multiple on the same page
    const allVideoSections = [];
    document.querySelectorAll(".o_omnigo_video_scroll_section").forEach(sec => {
        const vid = sec.querySelector(".o_omnigo_video_scroll_video");
        if (vid) allVideoSections.push({ sec, vid, seeking: false });
    });

    if (!heroHost || !bottomModelHost || !scrollHost) {
        console.warn("[loader] early exit — missing host element(s), script will not run on this page");
        return;
    }

    // ----------------------------
    // Text animation
    // ----------------------------
    const textEl = heroHost.querySelector(".o_three_canvas_text");
    if (textEl) {
        const text = (textEl.textContent || "").trim();
        textEl.textContent = "";

        [...text].forEach((char, index) => {
            const span = document.createElement("span");
            span.className = "letter";
            span.textContent = char === " " ? "\u00A0" : char;
            span.style.animationDelay = `${index * 0.16}s`;
            textEl.appendChild(span);
        });

        textEl.classList.add("is-ready");
    }

    let THREE;
    let GLTFLoader;
    let LoopPingPong;

    console.log("[loader] fetching Three.js from CDN…");
    try {
        THREE = await import("https://esm.sh/three@0.180.0");
        ({ GLTFLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/GLTFLoader.js"));

        LoopPingPong = THREE.LoopPingPong;
        console.log("[loader] Three.js ready");
    } catch (err) {
        console.error("[loader] Failed to load Three.js:", err);
        return;
    }

    const modelBasePath = "/prowebsite/static/src/models/";
    const adapterModelPath = "/prowebsite/static/src/models/BLK2GO_Adapter_V02B.glb";
    const animatedModelPath = "/prowebsite/static/src/models/blk2go_with_adapter_anim/scene.gltf";
    const animatedTexturePath = "/prowebsite/static/src/models/blk2go_with_adapter_anim/BLK2GO_with_Adapter_Textures/";

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

            console.log("[loader] fetching adapter GLB:", adapterModelPath);
            adapterLoader.load(
                adapterModelPath,
                (gltf) => {
                    console.log("[loader] adapter GLB loaded");
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
    // Top hero scene
    // ----------------------------
    const heroScene = new THREE.Scene();

    const heroCamera = new THREE.PerspectiveCamera(
        45,
        heroHost.clientWidth / heroHost.clientHeight,
        0.1,
        1000
    );
    heroCamera.position.set(0, 0, 3);

    const heroRenderer = createRenderer(heroHost, "4");
    addSoftProductLights(heroScene);

    let heroModel = null;
    let heroWrapper = null;
    let dropAnimationStart = null;
    const dropDuration = 1400;

    let mouseTargetX = 0;
    let mouseTargetY = 0;
    let mouseCurrentX = 0;
    let mouseCurrentY = 0;
    const maxOffsetX = 0.35;
    const maxOffsetY = 0.22;
    const mouseEase = 0.06;

    heroHost.addEventListener("mousemove", (event) => {
        const rect = heroHost.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;

        mouseTargetX = clamp(-x * maxOffsetX, -maxOffsetX, maxOffsetX);
        mouseTargetY = clamp(-y * maxOffsetY, -maxOffsetY, maxOffsetY);
    });

    heroHost.addEventListener("mouseleave", () => {
        mouseTargetX = 0;
        mouseTargetY = 0;
    });

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

    const gltfLoader = new GLTFLoader();
    const textureLoader = new THREE.TextureLoader();

    function loadTexture(url, isColor = false) {
        return new Promise((resolve, reject) => {
            textureLoader.load(
                url,
                (texture) => {
                    if (isColor) {
                        texture.colorSpace = THREE.SRGBColorSpace;
                    }
                    texture.flipY = false;
                    resolve(texture);
                },
                undefined,
                reject
            );
        });
    }

    async function loadAnimatedModelTextures() {
        const [
            colorMap,
            baseColorMap,
            metallicMap,
            roughnessMap,
            metalnessMap,
            roughnessAltMap,
        ] = await Promise.all([
            loadTexture(`${animatedTexturePath}BLK2GO_color.jpg`, true).catch(() => null),
            loadTexture(`${animatedTexturePath}BLK2GO_low_poly_01_blinn1SG_BaseColor.png`, true).catch(() => null),
            loadTexture(`${animatedTexturePath}BLK2GO_low_poly_01_blinn1SG_Metallic.png`, false).catch(() => null),
            loadTexture(`${animatedTexturePath}BLK2GO_low_poly_01_blinn1SG_Roughness.png`, false).catch(() => null),
            loadTexture(`${animatedTexturePath}BLK2GO_metalness.jpg`, false).catch(() => null),
            loadTexture(`${animatedTexturePath}BLK2GO_roughness1.jpg`, false).catch(() => null),
        ]);

        return {
            colorMap: baseColorMap || colorMap || null,
            metallicMap: metallicMap || metalnessMap || null,
            roughnessMap: roughnessMap || roughnessAltMap || null,
        };
    }

    console.log("[loader] fetching animated GLTF:", animatedModelPath);
    gltfLoader.load(
        animatedModelPath,
        async (gltf) => {
            console.log("[loader] animated GLTF loaded");
            const obj = gltf.scene;

            let textureSet = {
                colorMap: null,
                metallicMap: null,
                roughnessMap: null,
            };

            try {
                textureSet = await loadAnimatedModelTextures();
                console.log("Animated model textures loaded:", textureSet);
            } catch (err) {
                console.warn("Could not load one or more animated model textures:", err);
            }

            obj.traverse((child) => {
                if (!child.isMesh) {
                    return;
                }

                child.castShadow = false;
                child.receiveShadow = false;

                const existingMaterial = Array.isArray(child.material)
                    ? child.material[0]
                    : child.material;

                let material;

                if (existingMaterial && existingMaterial.isMeshStandardMaterial) {
                    material = existingMaterial.clone();
                } else {
                    material = new THREE.MeshStandardMaterial({
                        color: 0xffffff,
                        metalness: 0.25,
                        roughness: 0.65,
                        side: THREE.DoubleSide,
                    });
                }

                if (textureSet.colorMap) {
                    material.map = textureSet.colorMap;
                }

                if (textureSet.metallicMap) {
                    material.metalnessMap = textureSet.metallicMap;
                    material.metalness = 1.0;
                }

                if (textureSet.roughnessMap) {
                    material.roughnessMap = textureSet.roughnessMap;
                    material.roughness = 1.0;
                }

                material.side = THREE.DoubleSide;
                material.needsUpdate = true;

                child.material = material;
            });

            const initialBox = new THREE.Box3().setFromObject(obj);
            const initialSize = initialBox.getSize(new THREE.Vector3());
            const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);

            if (maxAxis > 0) {
                const scale = 1.7 / maxAxis;
                obj.scale.setScalar(scale);
            }

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
                console.warn("No animations found in scene.gltf");
            }

            updateLoadingProgress("animated GLTF");
        },
        undefined,
        (error) => {
            console.error("[loader] animated GLTF failed:", error);
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

    function isLargeScreen() {
        return window.matchMedia("(min-width: 992px)").matches;
    }

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
                <h3 class="o_three_scroll_feature_title">BLK2GO Attachment Interface</h3>
                <p class="o_three_scroll_feature_body">The top face is precision-machined to grip the BLK2GO handle securely, distributing load evenly across the clamp surface to eliminate vibration and scanner wobble during movement.</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_back">
                <h3 class="o_three_scroll_feature_title">One-Touch Release Button</h3>
                <p class="o_three_scroll_feature_body">The oversized rear button is designed to be operated with a single press — even in thick work gloves or high-pressure field conditions. One push cleanly ejects the OmniGO from any mount without fumbling.</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_hatch">
                <h3 class="o_three_scroll_feature_title">Quick-Release Latch</h3>
                <p class="o_three_scroll_feature_body">A single press of the side button disengages the spring-loaded latch, freeing the scanner in seconds. Re-attach with one hand — it clicks and locks automatically, no tools required.</p>
            </div>
            <div class="o_three_scroll_feature_detail o_three_scroll_feature_detail_screw">
                <h3 class="o_three_scroll_feature_title">Universal Tripod Mount</h3>
                <p class="o_three_scroll_feature_body">The bottom face carries a standard ¼″-20 thread, putting the BLK2GO on any tripod, monopod, survey pole, or camera arm — opening up hands-free and stationary scanning workflows.</p>
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
    }

    // ─── Scroll animation timing constants ───────────────────────────────────────
    // Each of the 4 features occupies one PHASE slot:
    //   [0 … TRANS)      — model animates to the new pose
    //   [TRANS … PHASE)  — model holds still; callout is visible   ← dwell
    // 4 × PHASE = 0.88; remaining 0.12 = return-to-rest transition.
    // All four dwell windows are exactly DWELL wide → consistent pause per feature.
    const SCROLL_TRANS = 0.08;                    // 8 % per transition
    const SCROLL_DWELL = 0.14;                    // 14 % per dwell
    const SCROLL_PHASE = SCROLL_TRANS + SCROLL_DWELL; // 0.22 per feature

    function updateScrollHotspots() {
        if (!scrollHotspotLayer) {
            return;
        }

        const show = (el, condition) => el && el.classList.toggle("is-visible", condition);
        const p = scrollAnimProgress;
        const T = SCROLL_TRANS, PH = SCROLL_PHASE;

        // Each feature is visible only during its dwell window (model has finished moving)
        const inAttachment = p >= T        && p <= PH;
        const inBack       = p >= PH + T   && p <= PH * 2;
        const inHatch      = p >= PH * 2 + T && p <= PH * 3;
        const inScrew      = p >= PH * 3 + T && p <= PH * 4;

        if (scrollDetailPanel) {
            show(scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_attachment"), inAttachment);
            show(scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_back"),       inBack);
            show(scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_hatch"),      inHatch);
            show(scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_screw"),      inScrew);
        }

        if (scrollMobileLabels) {
            show(scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_attachment"), inAttachment);
            show(scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_back"),       inBack);
            show(scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_hatch"),      inHatch);
            show(scrollMobileLabels.querySelector(".o_three_scroll_mobile_label_screw"),      inScrew);
        }
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

    // Hero adapter clone
    {
        const obj = createAdapterClone();
        obj.rotation.x = -0.25;
        obj.rotation.z = 0.12;

        heroModel = obj;
        heroWrapper = new THREE.Group();
        heroWrapper.add(heroModel);
        heroWrapper.position.set(0, 3.5, 0);
        heroScene.add(heroWrapper);

        dropAnimationStart = null;
        heroWrapper.position.y = 3.5;
    }

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
    // Resize
    // ----------------------------
    function onResize() {
        heroCamera.aspect = heroHost.clientWidth / heroHost.clientHeight;
        heroCamera.updateProjectionMatrix();
        heroRenderer.setSize(heroHost.clientWidth, heroHost.clientHeight);

        bottomCamera.aspect = bottomModelHost.clientWidth / bottomModelHost.clientHeight;
        bottomCamera.updateProjectionMatrix();
        bottomRenderer.setSize(bottomModelHost.clientWidth, bottomModelHost.clientHeight);

        scrollCamera.aspect = scrollHost.clientWidth / scrollHost.clientHeight;
        scrollCamera.updateProjectionMatrix();
        scrollRenderer.setSize(scrollHost.clientWidth, scrollHost.clientHeight);
    }

    window.addEventListener("resize", onResize);

    // omnigo scroll video sections — scrub all of them independently
    allVideoSections.forEach(entry => {
        const { vid } = entry;
        vid.pause();
        vid.addEventListener("seeked", () => { entry.seeking = false; }, { passive: true });
        vid.addEventListener("play", () => { vid.pause(); }, { passive: true });
    });

    function updateOmnigoScrollVideo() {
        allVideoSections.forEach(entry => {
            const { sec, vid } = entry;
            if (!vid.duration || vid.readyState < 2) return;
            if (entry.seeking) return;

            const rect = sec.getBoundingClientRect();
            const viewportH = window.innerHeight || document.documentElement.clientHeight;
            const totalScrollable = rect.height - viewportH;
            if (totalScrollable <= 0) return;

            const progress = clamp(-rect.top / totalScrollable, 0, 1);
            const targetTime = progress * vid.duration;

            if (Math.abs(vid.currentTime - targetTime) > 0.05) {
                entry.seeking = true;
                vid.currentTime = targetTime;
            }
        });
    }

    if (omnigoScrollVideo) {
        console.log("[loader] scroll video found, readyState:", omnigoScrollVideo.readyState, "src:", omnigoScrollVideo.currentSrc || "(not set yet)");
        if (omnigoScrollVideo.readyState >= 1) {
            console.log("[loader] scroll video metadata already ready");
            updateLoadingProgress("scroll video (immediate)");
        } else {
            console.log("[loader] waiting for scroll video loadedmetadata…");
            omnigoScrollVideo.addEventListener(
                "loadedmetadata",
                () => {
                    console.log("[loader] scroll video metadata loaded");
                    updateLoadingProgress("scroll video");
                },
                { once: true }
            );
        }
    } else {
        console.log("[loader] no scroll video element found, skipping");
        updateLoadingProgress("scroll video (skipped)");
    }

    // ----------------------------
    // Animation loop
    // ----------------------------
    function animate(now) {
        requestAnimationFrame(animate);

        const delta = bottomClock.getDelta();

        if (heroWrapper && userEnteredPage) {
            if (dropAnimationStart !== null) {
                const elapsed = now - dropAnimationStart;
                const t = clamp(elapsed / dropDuration, 0, 1);
                const eased = easeOutCubic(t);
                heroWrapper.position.y = 3.5 * (1 - eased);

                if (t >= 1) {
                    dropAnimationStart = null;
                    heroWrapper.position.y = 0;
                }
            }

            mouseCurrentX += (mouseTargetX - mouseCurrentX) * mouseEase;
            mouseCurrentY += (mouseTargetY - mouseCurrentY) * mouseEase;

            heroWrapper.position.x = mouseCurrentX;
            if (dropAnimationStart === null) {
                heroWrapper.position.y = mouseCurrentY;
            }

            if (heroModel) {
                heroModel.rotation.y += 0.01;
            }
        }

        if (bottomWrapper && bottomShouldAutoRotate(now)) {
            bottomWrapper.rotation.y += bottomAutoRotateSpeed;
        }

        if (bottomMixer) {
            bottomMixer.update(delta);
        }

        updateOmnigoScrollVideo();

        updateScrollSectionProgress();
        applyScrollSectionPose();

        heroRenderer.render(heroScene, heroCamera);
        bottomRenderer.render(bottomScene, bottomCamera);
        scrollRenderer.render(scrollScene, scrollCamera);
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

        const productId = parseInt(buyInner.dataset.productId, 10);
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

        // jQuery.ajax is always available on Odoo website pages and — unlike raw
        // fetch — automatically adds X-Requested-With: XMLHttpRequest, which Odoo's
        // middleware requires to recognise the request as an AJAX/JSON-RPC call.
        async function callCartUpdate(qty) {
            const jq = window.$ || window.jQuery;
            return new Promise((resolve, reject) => {
                jq.ajax({
                    url: "/shop/cart/update",
                    method: "POST",
                    contentType: "application/json",
                    data: JSON.stringify({
                        jsonrpc: "2.0",
                        method: "call",
                        id: Math.floor(Math.random() * 1e9),
                        params: { product_id: productId, add_qty: qty },
                    }),
                    success(data) {
                        if (data.error) {
                            const msg = data.error.data?.message || data.error.message || "Cart error";
                            reject(new Error(msg));
                        } else {
                            resolve(data.result);
                        }
                    },
                    error(xhr) {
                        const preview = xhr.responseText?.slice(0, 300) || "";
                        console.error("[buy] cart update HTTP error:", xhr.status, preview);
                        reject(new Error(`Cart error (HTTP ${xhr.status})`));
                    },
                });
            });
        }

        // Sync Odoo's header cart badge (.my_cart_quantity) with the updated quantity
        function syncCartBadge(result) {
            const newQty = result?.cart_quantity;
            if (newQty === undefined) return;
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
});