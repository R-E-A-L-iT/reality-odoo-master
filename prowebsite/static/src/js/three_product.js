/** @odoo-module **/

import { whenReady } from "@odoo/owl";

console.log("three_product.js file loaded");

whenReady(async () => {
    console.log("three_product.js whenReady fired");

    const host = document.getElementById("three-product-canvas");
    if (!host) {
        console.warn("No #three-product-canvas found");
        return;
    }

    const heroSection = host.closest(".o_three_hero");

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
        console.log("Three.js loaded from CDN", THREE);
        console.log("OBJLoader loaded from CDN", OBJLoader);
        console.log("MTLLoader loaded from CDN", MTLLoader);
    } catch (err) {
        console.error("Failed to load Three.js from CDN:", err);
        return;
    }

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(
        45,
        host.clientWidth / host.clientHeight,
        0.1,
        1000
    );
    camera.position.set(0, 0, 5);

    const renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(host.clientWidth, host.clientHeight);
    renderer.setClearColor(0x000000, 0);
    renderer.domElement.style.position = "absolute";
    renderer.domElement.style.inset = "0";
    renderer.domElement.style.zIndex = "2";
    renderer.domElement.style.background = "transparent";
    host.appendChild(renderer.domElement);

    const ambientLight = new THREE.AmbientLight(0xffffff, 4.0);
    scene.add(ambientLight);

    const hemiLight = new THREE.HemisphereLight(0xffffff, 0x666666, 3.0);
    hemiLight.position.set(0, 1, 0);
    scene.add(hemiLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 4.2);
    dirLight1.position.set(5, 8, 6);
    scene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 2.8);
    dirLight2.position.set(-5, 4, 5);
    scene.add(dirLight2);

    const cameraLight = new THREE.DirectionalLight(0xffffff, 5.2);
    cameraLight.position.set(0, 0, 8);
    cameraLight.target.position.set(0, 0, 0);
    scene.add(cameraLight);
    scene.add(cameraLight.target);

    const topLight = new THREE.DirectionalLight(0xffffff, 1.8);
    topLight.position.set(0, 8, 2);
    topLight.target.position.set(0, 0, 0);
    scene.add(topLight);
    scene.add(topLight.target);

    const rimLight = new THREE.DirectionalLight(0xffffff, 2.0);
    rimLight.position.set(0, 3, -6);
    rimLight.target.position.set(0, 0, 0);
    scene.add(rimLight);
    scene.add(rimLight.target);

    let adapterModel = null;
    let adapterWrapper = null;

    let scannerModel = null;
    let scannerWrapper = null;

    let dropAnimationStart = null;
    const dropDuration = 1400;

    // Mouse interaction state (disabled for now)
    let mouseTargetX = 0;
    let mouseTargetY = 0;
    let mouseCurrentX = 0;
    let mouseCurrentY = 0;

    const maxOffsetX = 0.35;
    const maxOffsetY = 0.22;
    const mouseEase = 0.06;

    const modelBasePath = "/prowebsite/static/src/models/";

    function easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    function clamp(value, min, max) {
        return Math.max(min, Math.min(max, value));
    }

    function loadObjWithMtl(objFile, mtlFile) {
        return new Promise((resolve, reject) => {
            const mtlLoader = new MTLLoader();
            mtlLoader.setPath(modelBasePath);

            mtlLoader.load(
                mtlFile,
                function (materials) {
                    materials.preload();

                    const objLoader = new OBJLoader();
                    objLoader.setMaterials(materials);
                    objLoader.setPath(modelBasePath);

                    objLoader.load(
                        objFile,
                        function (obj) {
                            obj.traverse(function (child) {
                                if (child.isMesh && child.material) {
                                    if (Array.isArray(child.material)) {
                                        child.material.forEach((mat) => {
                                            mat.side = THREE.DoubleSide;
                                        });
                                    } else {
                                        child.material.side = THREE.DoubleSide;
                                    }
                                }
                            });
                            resolve(obj);
                        },
                        undefined,
                        function (error) {
                            reject(error);
                        }
                    );
                },
                undefined,
                function (error) {
                    reject(error);
                }
            );
        });
    }

    function normalizeAndCenterObject(obj, targetSize = 1.1) {
        const initialBox = new THREE.Box3().setFromObject(obj);
        const initialSize = initialBox.getSize(new THREE.Vector3());
        const maxAxis = Math.max(initialSize.x, initialSize.y, initialSize.z);

        if (maxAxis > 0) {
            const scale = targetSize / maxAxis;
            obj.scale.setScalar(scale);
        }

        const box = new THREE.Box3().setFromObject(obj);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        obj.position.set(-center.x, -center.y, -center.z);

        return { box, center, size };
    }

    function getScannerScrollProgress() {
        if (!heroSection) {
            return 0;
        }

        const rect = heroSection.getBoundingClientRect();
        const vh = window.innerHeight || 1;

        // 0 when hero just starts entering viewport bottom
        // 1 when hero top reaches top of viewport
        const raw = (vh - rect.top) / vh;

        return clamp(raw, 0, 1);
    }

    function updateMouseTarget(clientX, clientY) {
        const rect = host.getBoundingClientRect();
        const centerX = rect.left + rect.width / 2;
        const centerY = rect.top + rect.height / 2;

        const nx = (clientX - centerX) / (rect.width / 2);
        const ny = (clientY - centerY) / (rect.height / 2);

        mouseTargetX = clamp(-nx, -1, 1) * maxOffsetX;
        mouseTargetY = clamp(ny, -1, 1) * maxOffsetY;
    }

    // Temporarily disabled mouse push effect
    /*
    host.addEventListener("mousemove", (event) => {
        updateMouseTarget(event.clientX, event.clientY);
    });

    host.addEventListener("mouseleave", () => {
        mouseTargetX = 0;
        mouseTargetY = 0;
    });

    host.addEventListener("touchmove", (event) => {
        if (event.touches && event.touches[0]) {
            updateMouseTarget(event.touches[0].clientX, event.touches[0].clientY);
        }
    }, { passive: true });

    host.addEventListener("touchend", () => {
        mouseTargetX = 0;
        mouseTargetY = 0;
    });
    */

    try {
        const loadedAdapter = await loadObjWithMtl(
            "BLK2GO_Adapter.obj",
            "BLK2GO_Adapter.mtl"
        );

        const adapterInfo = normalizeAndCenterObject(loadedAdapter, 1.1);

        // Tilt disabled temporarily
        /*
        loadedAdapter.rotation.x = -0.25;
        loadedAdapter.rotation.z = 0.12;
        */

        adapterModel = loadedAdapter;
        adapterWrapper = new THREE.Group();
        adapterWrapper.add(adapterModel);
        scene.add(adapterWrapper);

        const size = adapterInfo.size;
        const fitHeightDistance = size.y / (2 * Math.tan((Math.PI * camera.fov) / 360));
        const fitWidthDistance = fitHeightDistance / camera.aspect;
        const distance = 1.8 * Math.max(fitHeightDistance, fitWidthDistance, size.z, 2);

        camera.position.set(0, 0, distance || 4);
        camera.lookAt(0, 0, 0);

        cameraLight.position.copy(camera.position);
        cameraLight.position.z += 2.5;
        cameraLight.target.position.set(0, 0, 0);

        // Keep original nice drop-in animation
        adapterWrapper.position.set(0, 3.5, 0);
        dropAnimationStart = performance.now();

        console.log("Adapter model loaded successfully", loadedAdapter);
    } catch (error) {
        console.error("Error loading adapter model:", error);
    }

    try {
        const loadedScanner = await loadObjWithMtl(
            "BLK2GO_Scanner.obj",
            "BLK2GO_Scanner.mtl"
        );

        normalizeAndCenterObject(loadedScanner, 1.05);

        scannerModel = loadedScanner;
        scannerWrapper = new THREE.Group();
        scannerWrapper.add(scannerModel);
        scene.add(scannerWrapper);

        // Start above the visible area
        scannerWrapper.position.set(0, 3.8, 0);

        console.log("Scanner model loaded successfully", loadedScanner);
    } catch (error) {
        console.error("Error loading scanner model:", error);
    }

    function animate(now) {
        requestAnimationFrame(animate);

        mouseCurrentX += (mouseTargetX - mouseCurrentX) * mouseEase;
        mouseCurrentY += (mouseTargetY - mouseCurrentY) * mouseEase;

        let adapterBaseY = 0;

        if (adapterWrapper && dropAnimationStart !== null) {
            const elapsed = now - dropAnimationStart;
            const progress = Math.min(elapsed / dropDuration, 1);
            const eased = easeOutCubic(progress);

            adapterBaseY = 3.5 * (1 - eased);

            if (progress >= 1) {
                dropAnimationStart = null;
                adapterBaseY = 0;
            }
        }

        if (adapterWrapper) {
            adapterWrapper.position.x = 0;
            adapterWrapper.position.y = adapterBaseY;
            adapterWrapper.rotation.y += 0.01;

            // Mouse repelling temporarily disabled
            /*
            adapterWrapper.position.x = mouseCurrentX;
            adapterWrapper.position.y = adapterBaseY + mouseCurrentY;
            */
        }

        if (scannerWrapper) {
            // Progress only while the hero is entering/occupying the viewport.
            // Once it reaches the end, page scrolling continues normally.
            const scrollProgress = getScannerScrollProgress();

            const scannerStartY = 3.8;
            const scannerEndY = 0.85; // tweak this after testing

            const easedScroll = easeOutCubic(scrollProgress);
            scannerWrapper.position.x = 0;
            scannerWrapper.position.y =
                scannerStartY + (scannerEndY - scannerStartY) * easedScroll;

            scannerWrapper.rotation.y += 0.01;
        }

        renderer.render(scene, camera);
    }

    animate(performance.now());

    window.addEventListener("resize", () => {
        const width = host.clientWidth;
        const height = host.clientHeight;

        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderer.setSize(width, height);
        camera.lookAt(0, 0, 0);

        cameraLight.position.copy(camera.position);
        cameraLight.position.z += 2.5;
        cameraLight.target.position.set(0, 0, 0);
    });
});