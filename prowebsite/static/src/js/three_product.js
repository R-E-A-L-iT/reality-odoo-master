/** @odoo-module **/

import { whenReady } from "@odoo/owl";

whenReady(async () => {
    const host = document.getElementById("three-product-canvas");
    if (!host) {
        return;
    }

    const overlayEl = document.getElementById("three-scroll-overlay");
    const overlayModelHost = document.getElementById("three-product-canvas-overlay-model");
    const sceneStage = host.querySelector(".o_three_scene_stage");
    const section = host.closest(".o_three_scroll_section");

    if (!section || !overlayEl || !overlayModelHost || !sceneStage) {
        console.warn("Three scroll section structure is incomplete.");
        return;
    }

    // ----------------------------
    // Text animation
    // ----------------------------
    const textEl = host.querySelector(".o_three_canvas_text");
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
    let OBJLoader;
    let MTLLoader;

    try {
        THREE = await import("https://esm.sh/three@0.180.0");
        ({ OBJLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/OBJLoader.js"));
        ({ MTLLoader } = await import("https://esm.sh/three@0.180.0/examples/jsm/loaders/MTLLoader.js"));
    } catch (err) {
        console.error("Failed to load Three.js:", err);
        return;
    }

    const modelBasePath = "/prowebsite/static/src/models/";

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function createRenderer(targetHost, zIndex = "2") {
        const renderer = new THREE.WebGLRenderer({
            antialias: true,
            alpha: true,
        });
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
        const ambient = new THREE.AmbientLight(0xffffff, variant === "dark" ? 2.0 : 2.6);
        scene.add(ambient);

        const hemi = new THREE.HemisphereLight(
            0xffffff,
            variant === "dark" ? 0x444444 : 0xbbbbbb,
            variant === "dark" ? 1.6 : 2.1
        );
        hemi.position.set(0, 1, 0);
        scene.add(hemi);

        const dir1 = new THREE.DirectionalLight(0xffffff, variant === "dark" ? 2.4 : 3.2);
        dir1.position.set(5, 8, 6);
        scene.add(dir1);

        const dir2 = new THREE.DirectionalLight(0xffffff, variant === "dark" ? 1.4 : 2.2);
        dir2.position.set(-5, 4, 5);
        scene.add(dir2);

        const front = new THREE.DirectionalLight(0xffffff, variant === "dark" ? 3.2 : 4.0);
        front.position.set(0, 0, 8);
        front.target.position.set(0, 0, 0);
        scene.add(front);
        scene.add(front.target);
    }

    function loadObjWithMtl({ objFile, mtlFile, onLoaded }) {
        const mtlLoader = new MTLLoader();
        mtlLoader.setPath(modelBasePath);

        mtlLoader.load(
            mtlFile,
            (materials) => {
                materials.preload();

                const objLoader = new OBJLoader();
                objLoader.setMaterials(materials);
                objLoader.setPath(modelBasePath);

                objLoader.load(
                    objFile,
                    (obj) => {
                        obj.traverse((child) => {
                            if (child.isMesh) {
                                child.castShadow = false;
                                child.receiveShadow = false;

                                if (child.material) {
                                    if (Array.isArray(child.material)) {
                                        child.material.forEach((mat) => {
                                            mat.side = THREE.DoubleSide;
                                        });
                                    } else {
                                        child.material.side = THREE.DoubleSide;
                                    }
                                }
                            }
                        });

                        onLoaded(obj);
                    },
                    undefined,
                    (error) => console.error(`Error loading OBJ ${objFile}:`, error)
                );
            },
            undefined,
            (error) => console.error(`Error loading MTL ${mtlFile}:`, error)
        );
    }

    // ----------------------------
    // Main scene
    // ----------------------------
    const mainScene = new THREE.Scene();

    const mainCamera = new THREE.PerspectiveCamera(
        45,
        sceneStage.clientWidth / sceneStage.clientHeight,
        0.1,
        1000
    );
    mainCamera.position.set(0, 0, 5);

    const mainRenderer = createRenderer(sceneStage, "2");
    addStandardLights(mainScene, "dark");

    let mainModel = null;
    let mainWrapper = null;
    let dropAnimationStart = null;
    const dropDuration = 1400;

    // small mouse interaction
    let mouseTargetX = 0;
    let mouseTargetY = 0;
    let mouseCurrentX = 0;
    let mouseCurrentY = 0;
    const maxOffsetX = 0.35;
    const maxOffsetY = 0.22;
    const mouseEase = 0.06;

    loadObjWithMtl({
        objFile: "BLK2GO_Adapter.obj",
        mtlFile: "BLK2GO_Adapter.mtl",
        onLoaded: (obj) => {
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
            obj.rotation.x = -0.25;
            obj.rotation.z = 0.12;

            mainModel = obj;
            mainWrapper = new THREE.Group();
            mainWrapper.add(mainModel);
            mainWrapper.position.set(0, 3.5, 0);
            mainScene.add(mainWrapper);

            dropAnimationStart = performance.now();
        },
    });

    // ----------------------------
    // Overlay scene (left panel)
    // ----------------------------
    const overlayScene = new THREE.Scene();

    const overlayCamera = new THREE.PerspectiveCamera(
        40,
        overlayModelHost.clientWidth / overlayModelHost.clientHeight,
        0.1,
        1000
    );
    overlayCamera.position.set(0, 0, 5);

    const overlayRenderer = createRenderer(overlayModelHost, "1");
    addStandardLights(overlayScene, "light");

    let overlayModel = null;
    let overlayWrapper = null;

    loadObjWithMtl({
        objFile: "BLK2GO_with_Adapter.obj",
        mtlFile: "BLK2GO_with_Adapter.mtl",
        onLoaded: (obj) => {
            const initialBox = new THREE.Box3().setFromObject(obj);
            const initialSize = initialBox.getSize(new THREE.Vector3());
            const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);

            if (maxAxis > 0) {
                const scale = 1.6 / maxAxis;
                obj.scale.setScalar(scale);
            }

            const box = new THREE.Box3().setFromObject(obj);
            const center = box.getCenter(new THREE.Vector3());

            obj.position.set(-center.x, -center.y, -center.z);
            obj.rotation.x = -0.12;
            obj.rotation.z = 0.06;

            overlayModel = obj;
            overlayWrapper = new THREE.Group();
            overlayWrapper.add(overlayModel);
            overlayWrapper.position.set(0, 0, 0);
            overlayScene.add(overlayWrapper);
        },
    });

    // ----------------------------
    // Manual internal scroll progress
    // ----------------------------
    let internalProgress = 0;
    let renderedProgress = 0;
    let touchStartY = null;

    function sectionRect() {
        return section.getBoundingClientRect();
    }

    function sectionCanCaptureScroll() {
        const rect = sectionRect();
        return rect.top <= 0 && rect.bottom >= window.innerHeight;
    }

    function shouldCaptureFromPointer(event) {
        const rect = host.getBoundingClientRect();
        const x = event.clientX;
        const y = event.clientY;
        return x >= rect.left && x <= rect.right && y >= rect.top && y <= rect.bottom;
    }

    function updateInternalProgress(deltaY) {
        const speed = 0.0016;
        const nextProgress = clamp(internalProgress + deltaY * speed, 0, 1);

        const canMoveInternally =
            (deltaY > 0 && internalProgress < 1) ||
            (deltaY < 0 && internalProgress > 0);

        if (!canMoveInternally) {
            return false;
        }

        internalProgress = nextProgress;
        return true;
    }

    function onWheel(event) {
        if (!sectionCanCaptureScroll()) {
            return;
        }

        if (!shouldCaptureFromPointer(event)) {
            return;
        }

        const didConsume = updateInternalProgress(event.deltaY);

        if (didConsume) {
            event.preventDefault();
        }
    }

    function onTouchStart(event) {
        if (!event.touches.length) {
            return;
        }
        touchStartY = event.touches[0].clientY;
    }

    function onTouchMove(event) {
        if (!event.touches.length || touchStartY === null) {
            return;
        }

        if (!sectionCanCaptureScroll()) {
            touchStartY = event.touches[0].clientY;
            return;
        }

        const touch = event.touches[0];
        const rect = host.getBoundingClientRect();
        const inHost =
            touch.clientX >= rect.left &&
            touch.clientX <= rect.right &&
            touch.clientY >= rect.top &&
            touch.clientY <= rect.bottom;

        if (!inHost) {
            touchStartY = touch.clientY;
            return;
        }

        const currentY = touch.clientY;
        const deltaY = touchStartY - currentY;

        const didConsume = updateInternalProgress(deltaY * 1.35);

        if (didConsume) {
            event.preventDefault();
        }

        touchStartY = currentY;
    }

    function onTouchEnd() {
        touchStartY = null;
    }

    function animateOverlay() {
        renderedProgress += (internalProgress - renderedProgress) * 0.12;
        overlayEl.style.transform = `translateY(${(1 - renderedProgress) * 100}%)`;
        requestAnimationFrame(animateOverlay);
    }

    animateOverlay();

    // ----------------------------
    // Mouse movement for main model
    // ----------------------------
    host.addEventListener("mousemove", (event) => {
        const rect = host.getBoundingClientRect();
        const x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        const y = ((event.clientY - rect.top) / rect.height) * 2 - 1;

        mouseTargetX = clamp(-x * maxOffsetX, -maxOffsetX, maxOffsetX);
        mouseTargetY = clamp(-y * maxOffsetY, -maxOffsetY, maxOffsetY);
    });

    host.addEventListener("mouseleave", () => {
        mouseTargetX = 0;
        mouseTargetY = 0;
    });

    // ----------------------------
    // Resize
    // ----------------------------
    function onResize() {
        mainCamera.aspect = sceneStage.clientWidth / sceneStage.clientHeight;
        mainCamera.updateProjectionMatrix();
        mainRenderer.setSize(sceneStage.clientWidth, sceneStage.clientHeight);

        overlayCamera.aspect = overlayModelHost.clientWidth / overlayModelHost.clientHeight;
        overlayCamera.updateProjectionMatrix();
        overlayRenderer.setSize(overlayModelHost.clientWidth, overlayModelHost.clientHeight);
    }

    window.addEventListener("resize", onResize);
    window.addEventListener("wheel", onWheel, { passive: false });
    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: false });
    window.addEventListener("touchend", onTouchEnd, { passive: true });
    window.addEventListener("touchcancel", onTouchEnd, { passive: true });

    // ----------------------------
    // Animation loop
    // ----------------------------
    function animate(now) {
        requestAnimationFrame(animate);

        if (mainWrapper) {
            if (dropAnimationStart !== null) {
                const elapsed = now - dropAnimationStart;
                const t = clamp(elapsed / dropDuration, 0, 1);
                const eased = easeOutCubic(t);
                mainWrapper.position.y = 3.5 * (1 - eased);

                if (t >= 1) {
                    dropAnimationStart = null;
                    mainWrapper.position.y = 0;
                }
            }

            mouseCurrentX += (mouseTargetX - mouseCurrentX) * mouseEase;
            mouseCurrentY += (mouseTargetY - mouseCurrentY) * mouseEase;

            mainWrapper.position.x = mouseCurrentX;
            if (dropAnimationStart === null) {
                mainWrapper.position.y = mouseCurrentY;
            }

            if (mainModel) {
                mainModel.rotation.y += 0.01;
            }
        }

        if (overlayWrapper && overlayModel) {
            overlayModel.rotation.y += 0.008;
        }

        mainRenderer.render(mainScene, mainCamera);
        overlayRenderer.render(overlayScene, overlayCamera);
    }

    requestAnimationFrame(animate);
});