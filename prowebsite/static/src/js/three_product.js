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
    heroCamera.position.set(0, 0, 5);

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
    }

    function updateScrollHotspots() {
        if (!scrollHotspotLayer) {
            return;
        }

        const attachmentCallout = scrollHotspotLayer.querySelector(".o_three_feature_callout_attachment");
        const hatchCallout = scrollHotspotLayer.querySelector(".o_three_feature_callout_hatch");
        const screwCallout = scrollHotspotLayer.querySelector(".o_three_feature_callout_screw");

        if (attachmentCallout) {
            attachmentCallout.classList.toggle(
                "is-visible",
                scrollAnimProgress >= 0.12 && scrollAnimProgress <= 0.23
            );
        }

        if (hatchCallout) {
            hatchCallout.classList.toggle(
                "is-visible",
                scrollAnimProgress >= 0.37 && scrollAnimProgress <= 0.48
            );
        }

        if (screwCallout) {
            screwCallout.classList.toggle(
                "is-visible",
                scrollAnimProgress >= 0.60 && scrollAnimProgress <= 0.73
            );
        }

        if (scrollDetailPanel) {
            const show = (el, condition) => el && el.classList.toggle("is-visible", condition);
            show(scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_attachment"), scrollAnimProgress >= 0.12 && scrollAnimProgress <= 0.23);
            show(scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_hatch"),      scrollAnimProgress >= 0.37 && scrollAnimProgress <= 0.48);
            show(scrollDetailPanel.querySelector(".o_three_scroll_feature_detail_screw"),      scrollAnimProgress >= 0.60 && scrollAnimProgress <= 0.73);
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

        // Per-phase eased progress (each phase spans 25% of scroll travel)
        const p1 = easeInOutCubic(clamp(t / 0.25, 0, 1));
        const p2 = easeInOutCubic(clamp((t - 0.25) / 0.25, 0, 1));
        const p3 = easeInOutCubic(clamp((t - 0.50) / 0.25, 0, 1));
        const p4 = easeOutCubic(clamp((t - 0.75) / 0.25, 0, 1));

        // Responsive: on large screens shift left and zoom more to give room for detail panel
        const desktop = isLargeScreen();
        const modelX      = desktop ? -0.7 : 0;
        const scaleStart  = desktop ? 1.50 : 1.30;
        const scalePeak   = desktop ? 1.85 : 1.55;

        const scale = t < 0.75 ? lerp(scaleStart, scalePeak, p1) : lerp(scalePeak, scaleStart, p4);
        scrollWrapper.scale.setScalar(scale);
        scrollWrapper.position.set(modelX, 0, 0);

        // Model X (pitch):
        //   Phase 1 — tilt back to show top face (attachment interface)
        //   Phase 2 — bring upright while swinging Y to show side face (latch button)
        //   Phase 3 — tip forward to show bottom face (screw) while swinging Y back
        //   Phase 4 — return to rest
        let modelX;
        if (t < 0.25) {
            modelX = lerp(0, TOP_PITCH, p1);
        } else if (t < 0.50) {
            modelX = lerp(TOP_PITCH, SIDE_PITCH, p2);
        } else if (t < 0.75) {
            modelX = lerp(SIDE_PITCH, BOTTOM_PITCH, p3);
        } else {
            modelX = lerp(BOTTOM_PITCH, 0, p4);
        }
        scrollModel.rotation.x = modelX;
        scrollModel.rotation.y = 0;
        scrollModel.rotation.z = 0;

        // Wrapper Y (yaw): swing 90° during phase 2 to expose side face, return during phase 3
        let wrapperY;
        if (t < 0.25) {
            wrapperY = baseY;
        } else if (t < 0.50) {
            wrapperY = lerp(baseY, baseY + Math.PI * 0.5, p2);
        } else if (t < 0.75) {
            wrapperY = lerp(baseY + Math.PI * 0.5, baseY, p3);
        } else {
            wrapperY = baseY;
        }
        scrollWrapper.rotation.y = wrapperY;

        // Wrapper Z (roll): flatten slightly during reveal phases for a cleaner view
        let wrapperZ;
        if (t < 0.25) {
            wrapperZ = lerp(baseZ, baseZ * 0.4, p1);
        } else if (t < 0.75) {
            wrapperZ = baseZ * 0.4;
        } else {
            wrapperZ = lerp(baseZ * 0.4, baseZ, p4);
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

    // omnigo scroll video section
    function updateOmnigoScrollVideo() {
        if (!omnigoScrollVideo || !omnigoVideoSection || !omnigoScrollVideo.duration) {
            return;
        }

        const rect = omnigoVideoSection.getBoundingClientRect();
        const viewportH = window.innerHeight || document.documentElement.clientHeight;

        const totalScrollable = rect.height - viewportH;

        if (totalScrollable <= 0) {
            return;
        }

        const progress = clamp(-rect.top / totalScrollable, 0, 1);
        const targetTime = progress * omnigoScrollVideo.duration;

        if (Math.abs(omnigoScrollVideo.currentTime - targetTime) > 0.03) {
            omnigoScrollVideo.currentTime = targetTime;
        }
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
});