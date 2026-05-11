/** @odoo-module **/

import { whenReady } from "@odoo/owl";

whenReady(async () => {
    const heroHost = document.getElementById("three-product-canvas");
    const bottomModelHost = document.getElementById("three-product-canvas-bottom-model");
    const scrollHost = document.getElementById("three-product-canvas-scroll");

    const omnigoScrollVideo = document.getElementById("omnigo-scroll-video");
    const omnigoVideoSection = omnigoScrollVideo
        ? omnigoScrollVideo.closest(".o_omnigo_video_scroll_section")
        : null;

    if (!heroHost || !bottomModelHost || !scrollHost) {
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

    try {
        THREE = await import("https://esm.sh/three@0.180.0");
        ({ GLTFLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/GLTFLoader.js"));

        LoopPingPong = THREE.LoopPingPong;
    } catch (err) {
        console.error("Failed to load Three.js:", err);
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
                    resolve(adapterPrototype);
                },
                undefined,
                reject
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
    addStandardLights(heroScene, "dark");

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

    gltfLoader.load(
        animatedModelPath,
        async (gltf) => {
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
        },
        undefined,
        (error) => {
            console.error("Error loading animated GLTF:", error);
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
    addStandardLights(scrollScene, "dark");

    let scrollModel = null;
    let scrollWrapper = null;

    const scrollSection = scrollHost.closest(".o_three_scroll_section");
    let scrollHotspotLayer = null;

    function createScrollHotspots() {
        if (!scrollHost) {
            return;
        }

        scrollHotspotLayer = document.createElement("div");
        scrollHotspotLayer.className = "o_three_scroll_hotspot_layer";

        scrollHotspotLayer.innerHTML = `
            <div class="o_three_feature_callout o_three_feature_callout_screw">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">Multi-use screw attachment</div>
            </div>

            <div class="o_three_feature_callout o_three_feature_callout_hatch">
                <div class="o_three_feature_dot"></div>
                <div class="o_three_feature_line_diagonal"></div>
                <div class="o_three_feature_line_under"></div>
                <div class="o_three_feature_label">Easily securable hatch</div>
            </div>
        `;

        scrollHost.appendChild(scrollHotspotLayer);
    }

    function updateScrollHotspots() {
        if (!scrollHotspotLayer) {
            return;
        }

        const screwCallout = scrollHotspotLayer.querySelector(".o_three_feature_callout_screw");
        const hatchCallout = scrollHotspotLayer.querySelector(".o_three_feature_callout_hatch");

        if (screwCallout) {
            screwCallout.classList.toggle(
                "is-visible",
                scrollAnimProgress >= 0.46 && scrollAnimProgress <= 0.58
            );
        }

        if (hatchCallout) {
            hatchCallout.classList.toggle(
                "is-visible",
                scrollAnimProgress >= 0.92
            );
        }
    }

    let scrollAnimProgress = 0;
    const scrollPixelsForFullAnimation = 1400;

    function isScrollSectionActive() {
        if (!scrollSection) {
            return false;
        }

        const rect = scrollSection.getBoundingClientRect();
        const viewportH = window.innerHeight || document.documentElement.clientHeight;

        return rect.top <= 0 && rect.bottom >= viewportH;
    }

    function applyScrollSectionPose() {
        if (!scrollModel || !scrollWrapper) {
            return;
        }

        const t = scrollAnimProgress;

        // Phase 1: original animation, 0% → 50%
        const phase1 = clamp(t / 0.5, 0, 1);

        // Phase 2: new animation, 50% → 100%
        const phase2 = clamp((t - 0.5) / 0.5, 0, 1);

        // Smooth the second phase a little
        const phase2Ease = easeOutCubic(phase2);

        /*
        * Phase 1:
        * Bottom face rotates toward camera.
        */
        scrollModel.rotation.x = lerp(0, -Math.PI / 2, phase1);
        scrollModel.rotation.y = 0;
        scrollModel.rotation.z = 0;

        /*
        * Wrapper handles camera-facing rotations.
        *
        * Phase 1:
        * Slight counter-clockwise diamond angle.
        *
        * Phase 2:
        * Continue counter-clockwise another ~90 degrees from camera perspective.
        */
        scrollWrapper.rotation.z =
            lerp(0, Math.PI / 7, phase1) +
            lerp(0, -Math.PI * 0.62, phase2Ease);

        /*
        * Phase 2.
        */
        scrollWrapper.rotation.x = lerp(0, Math.PI / 2, phase2Ease);

        scrollWrapper.rotation.y = 0;

        // Re-center the model during phase 2 after the rolling motion
        scrollWrapper.position.x = lerp(0, -0.55, phase2Ease);
        scrollWrapper.position.y = lerp(0.25, -0.35, phase2Ease);
        scrollWrapper.position.z = lerp(1.35, 1.2, phase2Ease);

        updateScrollHotspots();
    }

    function onScrollSectionWheel(event) {
        if (!scrollSection || !isScrollSectionActive()) {
            return;
        }

        const delta = event.deltaY;
        const nextProgress = clamp(
            scrollAnimProgress + delta / scrollPixelsForFullAnimation,
            0,
            1
        );

        const tryingToScrollPastStart = delta < 0 && scrollAnimProgress <= 0;
        const tryingToScrollPastEnd = delta > 0 && scrollAnimProgress >= 1;

        if (tryingToScrollPastStart || tryingToScrollPastEnd) {
            return;
        }

        event.preventDefault();
        event.stopPropagation();

        scrollAnimProgress = nextProgress;
        applyScrollSectionPose();
    }

    if (scrollSection) {
        scrollSection.addEventListener("wheel", onScrollSectionWheel, { passive: false });
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

        dropAnimationStart = performance.now();
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

    // ----------------------------
    // Animation loop
    // ----------------------------
    function animate(now) {
        requestAnimationFrame(animate);

        const delta = bottomClock.getDelta();

        if (heroWrapper) {
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

        heroRenderer.render(heroScene, heroCamera);
        bottomRenderer.render(bottomScene, bottomCamera);
        scrollRenderer.render(scrollScene, scrollCamera);
    }

    requestAnimationFrame(animate);
});